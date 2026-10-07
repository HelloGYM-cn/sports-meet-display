from PIL import Image, ImageDraw
import math

SS = 4
BASE = 512
S = BASE * SS

BG_TOP = (26, 42, 90)
BG_BOT = (6, 8, 15)
GOLD_DARK = (168, 120, 0)
GOLD = (255, 215, 0)
GOLD_LIGHT = (255, 241, 168)
DARK = (8, 16, 40)


def draw_icon():
    img = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    pad = int(S * 0.04)
    radius = int(S * 0.22)

    bg = Image.new("RGBA", (S, S), (0, 0, 0, 0))
    bgd = ImageDraw.Draw(bg)
    for y in range(S):
        t = y / S
        r = int(BG_TOP[0] * (1 - t) + BG_BOT[0] * t)
        g = int(BG_TOP[1] * (1 - t) + BG_BOT[1] * t)
        b = int(BG_TOP[2] * (1 - t) + BG_BOT[2] * t)
        bgd.line([(0, y), (S, y)], fill=(r, g, b, 255))

    mask = Image.new("L", (S, S), 0)
    ImageDraw.Draw(mask).rounded_rectangle(
        [pad, pad, S - pad, S - pad], radius=radius, fill=255
    )
    img.paste(bg, (0, 0), mask)

    cx, cy = S // 2, int(S * 0.56)
    R = int(S * 0.30)
    ring_w = int(S * 0.038)
    inner_R = R - ring_w

    crown_w = int(S * 0.10)
    crown_h = int(S * 0.06)
    d.rounded_rectangle(
        [cx - crown_w // 2, cy - R - crown_h,
         cx + crown_w // 2, cy - R + int(S * 0.01)],
        radius=int(S * 0.015), fill=GOLD
    )

    ear_w = int(S * 0.028)
    for sign in (-1, 1):
        x1 = cx + sign * (crown_w // 2 + int(S * 0.005))
        y1 = cy - R - int(S * 0.02)
        x2 = x1 + sign * int(S * 0.075)
        y2 = y1 + int(S * 0.075)
        d.line([(x1, y1), (x2, y2)], fill=GOLD, width=ear_w)

    d.ellipse([cx - R, cy - R, cx + R, cy + R], fill=GOLD)
    d.arc([cx - R, cy - R, cx + R, cy + R],
          start=200, end=340, fill=GOLD_LIGHT, width=int(S * 0.008))

    d.ellipse([cx - inner_R, cy - inner_R,
               cx + inner_R, cy + inner_R], fill=DARK)

    fine_R = inner_R - int(S * 0.008)
    d.ellipse([cx - fine_R, cy - fine_R,
               cx + fine_R, cy + fine_R],
              outline=GOLD_DARK, width=max(2, int(S * 0.004)))

    for i in range(12):
        ang = math.radians(i * 30 - 90)
        outer = fine_R - int(S * 0.010)
        if i % 3 == 0:
            length = int(S * 0.040)
            w = max(3, int(S * 0.013))
        else:
            length = int(S * 0.022)
            w = max(2, int(S * 0.007))
        x1 = cx + math.cos(ang) * outer
        y1 = cy + math.sin(ang) * outer
        x2 = cx + math.cos(ang) * (outer - length)
        y2 = cy + math.sin(ang) * (outer - length)
        d.line([(x1, y1), (x2, y2)], fill=GOLD, width=w)

    hour_ang = math.radians((10 + 10 / 60) * 30 - 90)
    hour_len = fine_R * 0.52
    d.line([(cx, cy),
            (cx + math.cos(hour_ang) * hour_len,
             cy + math.sin(hour_ang) * hour_len)],
           fill=GOLD, width=max(4, int(S * 0.020)))

    min_ang = math.radians(10 * 6 - 90)
    min_len = fine_R * 0.74
    d.line([(cx, cy),
            (cx + math.cos(min_ang) * min_len,
             cy + math.sin(min_ang) * min_len)],
           fill=GOLD, width=max(3, int(S * 0.015)))

    hub = int(S * 0.022)
    d.ellipse([cx - hub, cy - hub, cx + hub, cy + hub], fill=GOLD)
    hub2 = int(S * 0.010)
    d.ellipse([cx - hub2, cy - hub2, cx + hub2, cy + hub2], fill=DARK)

    return img.resize((BASE, BASE), Image.LANCZOS)


base = draw_icon()
base.save("icon_preview.png")
print("已生成 icon_preview.png")

sizes = [(16, 16), (24, 24), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
base.save("icon.ico", format="ICO", sizes=sizes)
print("已生成 icon.ico")