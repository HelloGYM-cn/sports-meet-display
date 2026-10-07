<div align="center">

# 运动会大屏成绩展示系统

**HelloGYM · v1.0.0**

一个基于 Python + FastAPI + PySide6 的运动会成绩大屏系统。
支持手机扫码录入、实时大屏展示、奖牌榜自动统计。

[![License: CC BY-NC 4.0](https://img.shields.io/badge/License-CC%20BY--NC%204.0-lightgrey.svg)](LICENSE)
[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)]()
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-teal.svg)]()
[![Platform](https://img.shields.io/badge/Platform-Windows-lightgrey.svg)]()

</div>

---

## ✨ 功能特性

- 🏅 **奥运转播风大屏** — 纯黑底 + 绿色成绩 + 竖色带，远距离可读
- 📱 **手机扫码录入** — 裁判用手机/平板浏览器即可录入，无需安装 App
- 🖥️ **双屏 / 单屏自适应** — 自动识别扩展屏，也支持单屏热键切换
- 🏆 **奖牌榜自动统计** — 按单位累计金银铜牌，实时更新
- 📊 **Excel 导入** — 支持从现有成绩表一键导入
- 🎬 **启动画面 + 品牌署名** — 内置 HelloGYM 品牌启动动画
- 🔒 **黑屏切换** — 一键隐藏画面，应急使用
- 📋 **下一场预告** — 大屏底部滚动显示
- 💾 **多项目缓存** — 切换项目不丢数据
- 🌐 **局域网运行** — 数据不上云，学生信息安全

---

## 🚀 快速开始

### 环境要求

- Windows 10 / 11
- Python 3.11 - 3.13

### 安装

```bash
git clone https://github.com/HelloGYM-cn/sports-meet-display.git
cd sports-meet-display
pip install -r requirements.txt
