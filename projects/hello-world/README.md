# Hello World

在 Mac mini 屏幕上显示"你好世界！----HOYO"字样。

## 功能

- 使用 Python + Pillow 生成包含中文文字的图片
- 自动在 macOS Preview 中打开显示

## 环境要求

- Python 3.8+
- macOS

## 安装

```bash
# 安装依赖
pip install -r requirements.txt
```

## 运行

```bash
python main.py
```

运行后会自动生成 `hello.png` 并在 Preview 中打开显示。

## 文件结构

```
hello-world/
├── main.py          # 主程序
├── requirements.txt # Python 依赖
├── README.md        # 说明文档
└── hello.png        # 生成的图片（运行后产生）
```
