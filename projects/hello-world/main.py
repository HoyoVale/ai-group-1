#!/usr/bin/env python3
"""
HelloWorld - 在 Mac mini 屏幕上显示"你好世界！----HOYO"
使用 Pillow 生成图片并用 macOS 预览显示
"""

from PIL import Image, ImageDraw, ImageFont
import subprocess
import sys
import os

def create_hello_image():
    # 创建图片 (800x200, 白色背景)
    width, height = 800, 200
    image = Image.new('RGB', (width, height), 'white')
    draw = ImageDraw.Draw(image)
    
    # 尝试加载中文字体
    text = "你好世界！----HOYO"
    font_size = 48
    font = None
    
    # macOS 常见中文字体路径
    font_paths = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/Supplemental/PingFang.ttc",
        "/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Supplemental/Songti.ttc",
    ]
    
    for font_path in font_paths:
        if os.path.exists(font_path):
            try:
                font = ImageFont.truetype(font_path, font_size)
                print(f"使用字体：{font_path}")
                break
            except Exception as e:
                continue
    
    if font is None:
        print("未找到中文字体，使用默认字体（中文可能显示异常）")
        font = ImageFont.load_default()
    
    # 计算文字位置（居中）
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]
    x = (width - text_width) // 2
    y = (height - text_height) // 2
    
    # 绘制文字
    draw.text((x, y), text, fill='black', font=font)
    
    # 保存图片
    output_path = os.path.join(os.path.dirname(__file__), 'hello.png')
    image.save(output_path)
    print(f"图片已保存：{output_path}")
    
    return output_path

def show_image(image_path):
    """在 macOS 上打开图片"""
    try:
        subprocess.run(['open', '-a', 'Preview', image_path], check=True)
        print("图片已在 Preview 中打开")
    except subprocess.CalledProcessError as e:
        print(f"打开图片失败：{e}")
        # 尝试默认应用
        subprocess.run(['open', image_path])

def main():
    print("生成 HelloWorld 图片...")
    image_path = create_hello_image()
    print("正在打开图片...")
    show_image(image_path)
    print("完成！")

if __name__ == '__main__':
    main()
