#!/usr/bin/env python3
# 粒子残核 —— 3D 立体电弧合成器 v5（规则版）
# 电弧：确定性倾斜圆轨道（无随机抖动/尖峰）-> SDF 圆柱截面着色（白热芯 / 琥珀边 / 侧向高光）
#       + 按 z 深度做亮度衰减（近观者亮、绕到背后变暗）+ 核心前/后分层遮挡
# 合成：全程预乘 alpha + 2x2 精确降采样
# 几何规则：统一倾角 + 三折对称（方位 0/120/240°）+ 统一粗细，强调"规整能量环"而非杂乱闪电
import numpy as np
from PIL import Image, ImageFilter
from collections import deque

SRC = "/Users/vivian/WrokSpace/recycle-bin/bad-mood-recycle-bin/images/Same_glass_object_as_the_refer_2026-09-15T05-23-53.png"
OUT = "/Users/vivian/WrokSpace/recycle-bin/bad-mood-recycle-bin/images/badge_particle_remnant_3d.png"

SS = 2
rng = np.random.default_rng(2026)
TAU = 2 * np.pi


# ---------------------------------------------------------------- 核心抠像
def cut_core():
    a = np.asarray(Image.open(SRC).convert("RGB")).astype(np.float64) / 255.0
    H, W = a.shape[:2]
    mx, mn = a.max(2), a.min(2)
    c = mx - mn
    strict = c > 0.10
    ys, xs = np.where(strict)
    cx, cy = (xs.min() + xs.max()) / 2.0, (ys.min() + ys.max()) / 2.0
    rcore = max(xs.max() - xs.min(), ys.max() - ys.min()) / 2.0

    a0 = np.clip((c - 0.03) / 0.11, 0, 1)
    a0 = np.maximum(a0, np.clip((0.80 - mn) / 0.15, 0, 1))

    # 用较松的阈值找玻璃轮廓 -> 洪泛填外部 -> 内部（含白色高光"洞"）补实
    body = a0 > 0.42
    outside = np.zeros((H, W), dtype=bool)
    dq = deque()
    for x in range(W):
        for y in (0, H - 1):
            if not body[y, x] and not outside[y, x]:
                outside[y, x] = True; dq.append((y, x))
    for y in range(H):
        for x in (0, W - 1):
            if not body[y, x] and not outside[y, x]:
                outside[y, x] = True; dq.append((y, x))
    while dq:
        y, x = dq.popleft()
        for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ny, nx = y + dy, x + dx
            if 0 <= ny < H and 0 <= nx < W and not outside[ny, nx] and not body[ny, nx]:
                outside[ny, nx] = True; dq.append((ny, nx))
    inside_hole = (~outside) & (~body)          # 玻璃内部被判成背景的"洞"
    a0[inside_hole] = 1.0

    sm = np.asarray(Image.fromarray((a0 * 255).astype(np.uint8), "L")
                    .filter(ImageFilter.GaussianBlur(4))).astype(np.float64) / 255.0
    alpha = np.clip((sm - 0.26) / 0.44, 0, 1)
    Y, X = np.mgrid[0:H, 0:W]
    dd = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    # 轮廓内不透明实体（避免深底透过半透明区泛灰），仅外缘柔和衰减
    disc = np.clip((rcore * 1.20 - dd) / (rcore * 0.20), 0, 1)
    disc = disc * disc * (3 - 2 * disc)
    alpha = np.maximum(alpha, disc)

    R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    mean = (R + G + B) / 3.0
    sb = 1.14
    rgb = np.stack([np.clip(mean + (R - mean) * sb, 0, 1),
                    np.clip(mean + (G - mean) * sb, 0, 1),
                    np.clip(mean + (B - mean) * sb, 0, 1)], axis=2)
    return rgb, alpha, cx, cy, rcore, H, W


# ---------------------------------------------------------------- 3D 电弧（规则版）
def orbit_arc(cx, cy, R, span_deg, tilt_deg, az_deg, t0_deg, n=200):
    """规则倾斜圆轨道的一段弧：平滑无抖动，确定性几何，仅保留 z 深度做前后遮挡。

    - tilt_deg：轨道平面法线与视轴(z)的夹角，决定椭圆扁率与前后穿越幅度（立体感来源）
    - az_deg  ：绕视轴旋转整个轨道平面，用于把多条弧排成对称 halo
    - span/t0 ：弧段起止，统一大弧长 -> 干净的"能量环"观感
    """
    th, az = np.deg2rad(tilt_deg), np.deg2rad(az_deg)
    nrm = np.array([np.sin(th) * np.cos(az), np.sin(th) * np.sin(az), np.cos(th)])
    nrm /= np.linalg.norm(nrm)
    t = np.array([1.0, 0, 0]) if abs(nrm[0]) < 0.9 else np.array([0, 1.0, 0])
    u = np.cross(nrm, t); u /= np.linalg.norm(u)
    w = np.cross(nrm, u)
    ts = np.linspace(np.deg2rad(t0_deg), np.deg2rad(t0_deg + span_deg), n)
    p = (np.cos(ts)[:, None] * u + np.sin(ts)[:, None] * w) * R
    screen = np.stack([cx + p[:, 0], cy - p[:, 1]], axis=1)
    return np.concatenate([screen, p[:, 2:3]], axis=1)


def split_runs(arc):
    z = arc[:, 2]
    runs, cur = [], [0]
    for i in range(1, len(z)):
        if (z[i] >= 0) == (z[cur[-1]] >= 0):
            cur.append(i)
        else:
            runs.append(cur); cur = [i]
    runs.append(cur)
    return [(arc[r], z[r[0]] >= 0) for r in runs if len(r) >= 2]


def p_over(bottom, top):
    return top + bottom * (1 - top[..., 3:4])


def down2(arr):
    h, w, ch = arr.shape
    return arr.reshape(h // 2, 2, w // 2, 2, ch).mean(axis=(1, 3))


def add_seg(cover, col, p0, p1, w0, w1, b0, b1, body, hot, spec_k, rim_c, rim_k):
    x0, y0 = p0; x1, y1 = p1
    pad = max(w0, w1) * 1.8 + 4
    Hc, Wc = cover.shape
    X0 = max(0, int(min(x0, x1) - pad)); X1 = min(Wc, int(max(x0, x1) + pad) + 1)
    Y0 = max(0, int(min(y0, y1) - pad)); Y1 = min(Hc, int(max(y0, y1) + pad) + 1)
    if X1 <= X0 or Y1 <= Y0:
        return
    ys, xs = np.mgrid[Y0:Y1, X0:X1]
    dx, dy = x1 - x0, y1 - y0
    L2 = dx * dx + dy * dy + 1e-9
    t = ((xs - x0) * dx + (ys - y0) * dy) / L2
    tc = np.clip(t, 0, 1)
    px = x0 + tc * dx; py = y0 + tc * dy
    d = np.sqrt((xs - px) ** 2 + (ys - py) ** 2)
    w = np.maximum(w0 + (w1 - w0) * tc, 1e-6)
    L = np.sqrt(L2)
    nx, ny = -dy / L, dx / L
    perp = (xs - x0) * nx + (ys - y0) * ny
    b = (b0 + (b1 - b0) * tc)[..., None]

    tt = np.clip(d / w, 0, 1)
    shade = np.sqrt(np.clip(1 - tt * tt, 0, 1))            # 圆柱截面
    emiss = shade ** 3.2                                    # 白热芯（窄，但留出金色管身）
    spec = np.exp(-((perp / w + 0.34) / 0.26) ** 2) * shade  # 侧向高光
    c = (body[None, None, :] * shade[..., None]
         + hot[None, None, :] * emiss[..., None]) * b
    c = np.clip(c + spec[..., None] * spec_k, 0, 1)

    a = np.clip((w - d) / 0.9, 0, 1)                        # 硬边（仅微羽化）
    # 暗金描边：把亮管从亮玻璃上"抠"出来，边界连续清晰
    a_rim = np.clip(1 - np.abs(d - w * 1.18) / (w * 0.34), 0, 1) * rim_k
    use_rim = a_rim > a
    c = np.where(use_rim[..., None], np.broadcast_to(rim_c[None, None, :], c.shape) * b, c)
    a = np.maximum(a, a_rim)
    sel = a > cover[Y0:Y1, X0:X1]
    col[Y0:Y1, X0:X1] = np.where(sel[..., None], c, col[Y0:Y1, X0:X1])
    cover[Y0:Y1, X0:X1] = np.where(sel, a, cover[Y0:Y1, X0:X1])


def render_layer(N, arcs, front):
    if front:
        body = np.array([255, 166, 62]) / 255.0
        hot = np.array([255, 250, 232]) / 255.0
        glowc = np.array([255, 198, 108]) / 255.0
        base_w, spec_k, dim, glow_k = 5.4, 0.95, 1.0, 0.50
        rim_c, rim_k = np.array([140, 74, 16]) / 255.0, 0.45
    else:
        body = np.array([242, 198, 132]) / 255.0
        hot = np.array([255, 248, 232]) / 255.0
        glowc = np.array([246, 206, 140]) / 255.0
        base_w, spec_k, dim, glow_k = 4.0, 0.75, 0.72, 0.30
        rim_c, rim_k = np.array([150, 96, 44]) / 255.0, 0.30

    M = N * SS
    cover = np.zeros((M, M))
    col = np.zeros((M, M, 3))

    for arc in arcs:
        P = arc[:, :2] * SS
        Z = arc[:, 2]
        sw = 1.0                                            # 统一粗细 -> 规则一致
        zmax = np.abs(Z).max() + 1e-6
        zn = np.clip(Z / zmax, -1, 1)
        # 深度亮度：正面(z大)亮；背面越远越暗
        if front:
            b = 0.62 + 0.38 * zn
        else:
            b = (0.85 - 0.45 * np.abs(zn)) * dim
        m = len(P)
        # 端点收成针尖（规则：仅末端 taper，中段恒为 1）
        taper = (0.14 + 0.86 * np.sin(np.linspace(0, np.pi, m)) ** 0.5) * sw
        for i in range(m - 1):
            add_seg(cover, col, tuple(P[i]), tuple(P[i + 1]),
                    base_w * taper[i] * SS, base_w * taper[i + 1] * SS,
                    float(b[i]), float(b[i + 1]), body, hot, spec_k, rim_c, rim_k)

    glow_a = np.asarray(Image.fromarray((cover * 255).astype(np.uint8), "L")
                        .filter(ImageFilter.GaussianBlur(3 * SS))).astype(np.float64) / 255.0
    glow_a = np.clip(glow_a, 0, 1) * glow_k

    layer = np.zeros((M, M, 4))
    layer[:, :, :3] = col * cover[..., None] + glowc[None, None, :] * glow_a[..., None]
    layer[:, :, 3] = cover + glow_a * (1 - cover)
    covN = down2(np.repeat(cover[..., None], 4, axis=2))[:, :, 0]
    return down2(layer), covN


def main():
    rgb, alpha, cx, cy, rcore, H, W = cut_core()
    N = W

    front, back = [], []
    TILT = 50                                  # 统一轨道倾角 -> 干净的椭圆 + 一致的前/后穿越（立体感）
    # (半径系数, 弧长°, 绕视轴方位°, 起始相位°) —— 三条弧三折对称、规则均匀
    ARCS = [
        (0.92, 215,   0,  10),                 # 内圈
        (1.08, 215, 120, 130),                 # 外圈 A（绕视轴转 120°）
        (1.20, 215, 240, 250),                 # 外圈 B（再转 120°）
    ]
    for Rf, span, az, t0 in ARCS:
        R = rcore * Rf
        arc = orbit_arc(cx, cy, R, span, TILT, az, t0)
        for run, is_front in split_runs(arc):
            (front if is_front else back).append(run)

    backL, _ = render_layer(N, back, False)
    frontL, frontC = render_layer(N, front, True)

    Y, X = np.mgrid[0:H, 0:W]
    dd = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
    tt = np.clip(1 - dd / (rcore * 1.5), 0, 1)
    gA = 0.12 * tt * tt
    auraP = np.zeros((H, W, 4))
    auraP[:, :, 0], auraP[:, :, 1], auraP[:, :, 2] = 1.0, 216 / 255, 198 / 255
    auraP[:, :, :3] *= gA[..., None]; auraP[:, :, 3] = gA

    coreP = np.zeros((H, W, 4))
    coreP[:, :, :3] = rgb * alpha[..., None]
    coreP[:, :, 3] = alpha

    comp = p_over(auraP, backL)
    comp = p_over(comp, coreP)

    # 前弧压在核心上：接触阴影（右下偏移）+ 暖色光溢出 -> 立体读感
    fc8 = (np.clip(frontC, 0, 1) * 255).astype(np.uint8)
    sh = np.asarray(Image.fromarray(fc8, "L").filter(ImageFilter.GaussianBlur(4))).astype(np.float64) / 255.0
    sh = np.roll(np.roll(sh, 4, axis=0), 3, axis=1)
    comp[:, :, :3] *= (1 - 0.18 * sh[..., None])

    bl = np.asarray(Image.fromarray(fc8, "L").filter(ImageFilter.GaussianBlur(11))).astype(np.float64) / 255.0
    comp[:, :, :3] += (np.array([255, 206, 130]) / 255.0) * (bl * 0.20)[..., None]

    comp = p_over(comp, frontL)
    comp[:, :, :3] = np.minimum(comp[:, :, :3], comp[:, :, 3:4])

    a = np.clip(comp[:, :, 3], 0, 1)
    safe = np.maximum(a, 1e-6)
    out = np.zeros((H, W, 4), dtype=np.uint8)
    out[:, :, :3] = np.clip(comp[:, :, :3] / safe[..., None], 0, 1) * 255
    out[:, :, 3] = a * 255
    img = Image.fromarray(out, "RGBA")
    arr = np.asarray(img)
    ys, xs = np.where(arr[:, :, 3] > 8)
    pad = 14
    img = img.crop((max(0, xs.min() - pad), max(0, ys.min() - pad),
                    min(W, xs.max() + pad), min(H, ys.max() + pad)))
    img.save(OUT)
    print("saved", OUT, img.size, "rcore", round(rcore), "front", len(front), "back", len(back))


if __name__ == "__main__":
    main()
