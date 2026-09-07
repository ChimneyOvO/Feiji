"""
生成飞记 (FeiJi) 高清多分辨率 Windows 图标 (.ico)
"""

from PIL import Image, ImageDraw


def create_app_icon(ico_path="feiji.ico"):
    # 以 256x256 高清母图绘制
    w, h = 256, 256
    img = Image.new("RGBA", (w, h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # 1. 绘制 Fluent Blue 圆角矩形背景
    pad = 16
    radius = 56
    draw.rounded_rectangle(
        [pad, pad, w - pad, h - pad],
        radius=radius,
        fill="#0078D4"
    )

    # 2. 绘制白色折纸飞机
    poly_norm = [
        (0.24, 0.50),  # 左翼
        (0.76, 0.24),  # 机头
        (0.52, 0.76),  # 右翼
        (0.44, 0.55),  # 机腹
    ]
    poly = [(int(x * w), int(y * h)) for x, y in poly_norm]
    draw.polygon(poly, fill="#FFFFFF")

    # 3. 绘制折痕高光
    fold_norm = [
        (0.76, 0.24),
        (0.44, 0.55)
    ]
    fold = [(int(x * w), int(y * h)) for x, y in fold_norm]
    draw.line(fold, fill="#D8E7F8", width=6)

    # 保存包含各种分辨率的高清图标
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(ico_path, format="ICO", sizes=sizes)
    print(f"成功生成多分辨率高清图标: {ico_path}")


if __name__ == "__main__":
    create_app_icon()
    import shutil
    shutil.copy2("feiji.ico", "dist/FeiJi_Setup_v1.0.0/feiji.ico")
