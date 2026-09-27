#!/usr/bin/env python3
# 白底抠像 v4：软 alpha + 径向圆窗收边 -> 干净圆形发光徽章（透明 PNG）
import numpy as np
from PIL import Image, ImageFilter
from collections import deque

SRC = "/Users/vivian/WrokSpace/recycle-bin/bad-mood-recycle-bin/images/Same_design_as_the_reference___2026-09-15T04-45-44.png"
OUT = "/Users/vivian/WrokSpace/recycle-bin/bad-mood-recycle-bin/images/badge_particle_remnant_3d.png"

im = Image.open(SRC).convert("RGB")
a = np.asarray(im).astype(np.float64) / 255.0
H, W = a.shape[:2]
mx, mn = a.max(2), a.min(2)
c = mx - mn

a0 = np.clip((c - 0.02) / 0.10, 0, 1)
a0 = np.maximum(a0, np.clip((0.82 - mn) / 0.14, 0, 1))

# 内部空洞补实
solid = a0 > 0.5
visit = np.zeros((H, W), dtype=bool)
dq = deque()
for x in range(W):
    for y in (0, H - 1):
        if not solid[y, x] and not visit[y, x]:
            visit[y, x] = True; dq.append((y, x))
for y in range(H):
    for x in (0, W - 1):
        if not solid[y, x] and not visit[y, x]:
            visit[y, x] = True; dq.append((y, x))
while dq:
    y, x = dq.popleft()
    for dy, dx in ((1, 0), (-1, 0), (0, 1), (0, -1)):
        ny, nx = y + dy, x + dx
        if 0 <= ny < H and 0 <= nx < W and not visit[ny, nx] and not solid[ny, nx]:
            visit[ny, nx] = True; dq.append((ny, nx))
a0[(~solid) & (~visit)] = 1.0

# 平滑 + 软映射
sm = np.asarray(Image.fromarray((a0 * 255).astype(np.uint8), "L")
                .filter(ImageFilter.GaussianBlur(6))).astype(np.float64) / 255.0
alpha = np.clip((sm - 0.28) / 0.42, 0, 1)

# 中心（按本体）
ys, xs = np.where(a0 > 0.5)
cx, cy = (xs.min() + xs.max()) / 2.0, (ys.min() + ys.max()) / 2.0

# 径向圆窗平滑收边（r 310->372 淡出）
Y, X = np.mgrid[0:H, 0:W]
dd = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
v = np.clip((372.0 - dd) / (372.0 - 310.0), 0, 1)
v = v * v * (3 - 2 * v)
alpha = alpha * v

R, G, B = a[:, :, 0], a[:, :, 1], a[:, :, 2]
mean = (R + G + B) / 3.0
sb = 1.12
Rr = np.clip(mean + (R - mean) * sb, 0, 1)
Gr = np.clip(mean + (G - mean) * sb, 0, 1)
Br = np.clip(mean + (B - mean) * sb, 0, 1)

# 克制暖光晕
Rg = 360.0
tt = np.clip(1 - dd / Rg, 0, 1)
glowA = 0.16 * tt * tt
glowC = np.array([1.0, 0.86, 0.81])

outA = alpha + glowA * (1 - alpha)
safe = np.maximum(outA, 1e-6)
outR = (Rr * alpha + glowC[0] * glowA * (1 - alpha)) / safe
outG = (Gr * alpha + glowC[1] * glowA * (1 - alpha)) / safe
outB = (Br * alpha + glowC[2] * glowA * (1 - alpha)) / safe

out = np.zeros((H, W, 4), dtype=np.uint8)
out[:, :, 0] = np.clip(outR, 0, 1) * 255
out[:, :, 1] = np.clip(outG, 0, 1) * 255
out[:, :, 2] = np.clip(outB, 0, 1) * 255
out[:, :, 3] = np.clip(outA, 0, 1) * 255

img = Image.fromarray(out, "RGBA")
ys2, xs2 = np.where(outA > 0.06)
pad = 16
img = img.crop((max(0, xs2.min() - pad), max(0, ys2.min() - pad), min(W, xs2.max() + pad), min(H, ys2.max() + pad)))
img.save(OUT)
print("saved", OUT, img.size, "center", cx, cy)
