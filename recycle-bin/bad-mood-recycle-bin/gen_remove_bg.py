#!/usr/bin/env python3
# 绿幕抠像 v2：键控 alpha + HSV 绿色残留扭向暖金 + 压绿 + 补暖光晕 -> 真透明 PNG
import numpy as np
from PIL import Image

SRC = "/Users/vivian/WrokSpace/recycle-bin/bad-mood-recycle-bin/images/Referring_to_the_reference_ima_2026-09-15T04-43-46.png"
OUT = "/Users/vivian/WrokSpace/recycle-bin/bad-mood-recycle-bin/images/badge_particle_remnant_3d.png"

im = Image.open(SRC).convert("RGB")
a = np.asarray(im).astype(np.float64) / 255.0
H, W = a.shape[:2]

# --- 1) 键控 alpha（基于绿度）---
greenness = a[:, :, 1] - np.maximum(a[:, :, 0], a[:, :, 2])
t0, t1 = 0.03, 0.32
alpha = np.clip((t1 - greenness) / (t1 - t0), 0, 1)
alpha[-175:, -430:] = 0.0  # 清右下角水印

# --- 2) HSV 色相校正：把残留绿色扭向暖金 ---
hsv = np.asarray(im.convert("HSV")).astype(np.float64)
Hc, Sc, Vc = hsv[:, :, 0], hsv[:, :, 1], hsv[:, :, 2]
is_green = (Hc >= 55) & (Hc <= 150)
w = np.where(is_green, np.clip(Sc / 255.0, 0, 1), 0.0)
Hc = np.where(is_green, Hc * (1 - w) + 26 * w, Hc)  # 26/255*360 ≈ 37° 橙色
Sc = Sc * (1 - 0.62 * w)
hsv2 = np.stack([Hc, Sc, Vc], axis=2).astype(np.uint8)
rgb = np.asarray(Image.fromarray(hsv2, "HSV").convert("RGB")).astype(np.float64) / 255.0
R, G, B = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]

# --- 3) 压绿：G 不超过 max(R,B) ---
Gf = np.minimum(G, np.maximum(R, B))
Rf, Bf = R.copy(), B.copy()

# --- 4) 内容包围盒 & 补暖光晕 ---
ys, xs = np.where(alpha > 0.2)
print("bbox", xs.min(), xs.max(), ys.min(), ys.max())
cx, cy = (xs.min() + xs.max()) / 2.0, (ys.min() + ys.max()) / 2.0
rad = max(xs.max() - xs.min(), ys.max() - ys.min()) / 2.0
Y, X = np.mgrid[0:H, 0:W]
dd = np.sqrt((X - cx) ** 2 + (Y - cy) ** 2)
glowA = np.clip(0.42 * np.exp(-(dd / (rad * 1.0)) ** 2), 0, 1)
glowC = np.array([1.0, 0.90, 0.80])

outA = alpha + glowA * (1 - alpha)
safe = np.maximum(outA, 1e-6)
outR = (Rf * alpha + glowC[0] * glowA * (1 - alpha)) / safe
outG = (Gf * alpha + glowC[1] * glowA * (1 - alpha)) / safe
outB = (Bf * alpha + glowC[2] * glowA * (1 - alpha)) / safe

out = np.zeros((H, W, 4), dtype=np.uint8)
out[:, :, 0] = np.clip(outR, 0, 1) * 255
out[:, :, 1] = np.clip(outG, 0, 1) * 255
out[:, :, 2] = np.clip(outB, 0, 1) * 255
out[:, :, 3] = np.clip(outA, 0, 1) * 255

img = Image.fromarray(out, "RGBA")
pad = 24
img = img.crop((max(0, xs.min() - pad), max(0, ys.min() - pad), min(W, xs.max() + pad), min(H, ys.max() + pad)))
img.save(OUT)
print("saved", OUT, img.size)
