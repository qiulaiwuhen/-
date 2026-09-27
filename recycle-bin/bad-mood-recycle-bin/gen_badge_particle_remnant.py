#!/usr/bin/env python3
# 程序化生成「粒子残核」徽章图（玻璃凝聚体 + 薄荷光晕 + 蓝绿电弧 + 深色遮罩）
# 用途：在 GEMINI_API_KEY 缺失、无法调用 nano-banana-pro 时的可用替代交付。
import math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

W = H = 1024
cx = cy = W / 2.0
ys, xs = np.mgrid[0:H, 0:W]
dx = xs - cx
dy = ys - cy
d = np.sqrt(dx * dx + dy * dy)

orbR = 210.0
arcR = 252.0

col = np.zeros((H, W, 3), dtype=np.float64)
alp = np.zeros((H, W), dtype=np.float64)

def composite(layer):
    global col, alp
    lr, lg, lb, la = layer[:, :, 0], layer[:, :, 1], layer[:, :, 2], layer[:, :, 3]
    la = np.clip(la, 0, 1)
    out_a = la + alp * (1 - la)
    safe = np.maximum(out_a, 1e-6)
    col[:, :, 0] = (lr * la + col[:, :, 0] * alp * (1 - la)) / safe
    col[:, :, 1] = (lg * la + col[:, :, 1] * alp * (1 - la)) / safe
    col[:, :, 2] = (lb * la + col[:, :, 2] * alp * (1 - la)) / safe
    alp[:] = out_a

def to_layer(rgba):
    return np.asarray(rgba).astype(np.float64) / 255.0

# 1) 深色半透明遮罩（中心暗、向外淡出，四角透明，适合做弹窗）
la = 0.92 * np.clip(1 - d / 520, 0, 1) ** 1.4
back = np.zeros((H, W, 4))
back[:, :, 0] = 10 / 255
back[:, :, 1] = 16 / 255
back[:, :, 2] = 24 / 255
back[:, :, 3] = la
composite(back)

# 2) 薄荷绿光晕（环形 glow，模糊）
inten = 0.78 * np.exp(-((d - (orbR + 95)) / 52) ** 2)
halo = np.zeros((H, W, 4))
halo[:, :, 0] = 127 / 255
halo[:, :, 1] = 212 / 255
halo[:, :, 2] = 166 / 255
halo[:, :, 3] = inten
halo = to_layer(Image.fromarray((halo * 255).astype(np.uint8), 'RGBA').filter(ImageFilter.GaussianBlur(13)))
composite(halo)

# 3) 半透明玻璃凝聚体（球体着色 + 菲涅尔边缘光 + 镜面高光）
inside = (d < orbR).astype(np.float64).reshape(H, W, 1)
nx = dx / orbR
ny = dy / orbR
nz = np.sqrt(np.maximum(orbR ** 2 - d ** 2, 0)) / orbR
L = np.array([-0.42, -0.58, 0.70])
L = L / np.linalg.norm(L)
ndot = nx * L[0] + ny * L[1] + nz * L[2]
diff = np.clip(ndot, 0, 1).reshape(H, W, 1)
base = np.array([40, 92, 86], dtype=np.float64).reshape(1, 1, 3)
hi = np.array([205, 248, 228], dtype=np.float64).reshape(1, 1, 3)
c3 = base + (hi - base) * diff * 0.85
rim = np.clip((d / orbR - 0.80) / 0.20, 0, 1).reshape(H, W, 1)
c3 = c3 + np.array([150, 232, 216], dtype=np.float64).reshape(1, 1, 3) * rim * 0.9
c3 = c3 + np.array([55, 150, 140], dtype=np.float64).reshape(1, 1, 3) * nz.reshape(H, W, 1) * 0.35
c3 = np.clip(c3, 0, 255)
alpha = inside * (0.62 + 0.34 * diff + 0.45 * rim)
alpha = np.clip(alpha, 0, 0.96)
orb = np.zeros((H, W, 4))
orb[:, :, 0] = c3[:, :, 0] / 255
orb[:, :, 1] = c3[:, :, 1] / 255
orb[:, :, 2] = c3[:, :, 2] / 255
orb[:, :, 3] = alpha[:, :, 0]
# 镜面高光（左上）
spec = np.exp(-(((dx + 72) ** 2 + (dy + 82) ** 2) / (60 ** 2)))
orb[:, :, 0] = np.clip(orb[:, :, 0] + spec * 0.9, 0, 1)
orb[:, :, 1] = np.clip(orb[:, :, 1] + spec * 0.95, 0, 1)
orb[:, :, 2] = np.clip(orb[:, :, 2] + spec * 1.0, 0, 1)
orb[:, :, 3] = np.clip(orb[:, :, 3] + spec * 0.8, 0, 0.98)
composite(orb)

# 4) 内部凝聚粒子（薄荷色光点，模糊）
rng = random.Random(20260915)
pinten = np.zeros((H, W))
for _ in range(48):
    a = rng.uniform(0, 2 * math.pi)
    rr = math.sqrt(rng.random()) * orbR * 0.8
    px = cx + math.cos(a) * rr
    py = cy + math.sin(a) * rr
    sig = rng.uniform(6, 14)
    pinten += np.exp(-(((dx - px) ** 2 + (dy - py) ** 2) / (sig ** 2))) * rng.uniform(0.5, 1.0)
pinten = np.clip(pinten, 0, 1)
part = np.zeros((H, W, 4))
part[:, :, 0] = 150 / 255
part[:, :, 1] = 240 / 255
part[:, :, 2] = 205 / 255
part[:, :, 3] = pinten * 0.9
part = to_layer(Image.fromarray((part * 255).astype(np.uint8), 'RGBA').filter(ImageFilter.GaussianBlur(3)))
composite(part)

# 5) 蓝绿色电弧闪电环绕（程序化抖动折线 + 高斯辉光）
def arc_points(r, start, span, segs, jitter):
    pts = []
    for i in range(segs + 1):
        a = start + span * (i / segs)
        rr = r + rng.uniform(-jitter, jitter)
        pts.append((cx + math.cos(a) * rr, cy + math.sin(a) * rr))
    return pts

arc_layer = Image.new('RGBA', (W, H), (0, 0, 0, 0))
ad = ImageDraw.Draw(arc_layer)
for _ in range(6):
    start = rng.uniform(0, 2 * math.pi)
    span = rng.uniform(0.4, 1.1) * (1 if rng.random() < 0.5 else -1)
    segs = 12
    pts = arc_points(arcR, start, span, segs, 14)
    ad.line(pts, fill=(110, 225, 205, 235), width=7, joint='curve')
    ad.line(pts, fill=(225, 255, 248, 255), width=3, joint='curve')
arc_layer = arc_layer.filter(ImageFilter.GaussianBlur(3.5))
composite(to_layer(arc_layer))

# 输出
out = np.zeros((H, W, 4), dtype=np.uint8)
out[:, :, 0] = np.clip(col[:, :, 0], 0, 1) * 255
out[:, :, 1] = np.clip(col[:, :, 1], 0, 1) * 255
out[:, :, 2] = np.clip(col[:, :, 2], 0, 1) * 255
out[:, :, 3] = np.clip(alp, 0, 1) * 255
path = '/Users/vivian/WrokSpace/recycle-bin/bad-mood-recycle-bin/images/badge_particle_remnant.png'
Image.fromarray(out, 'RGBA').save(path)
print('saved', path, out.shape)
