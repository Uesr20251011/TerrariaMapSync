# 🗺️ 泰拉瑞亚联机地图同步助手

通过 GitHub 仓库实现多人联机地图同步的桌面小工具。

## ✨ 功能

- 🔍 **自动发现** — 自动识别本地泰拉瑞亚 Worlds 文件夹中的地图
- 📤 **一键上传** — 选择地图上传至 GitHub，自动添加日期前缀（如 `20260802我的世界.wld`）
- 📥 **版本下载** — 查看云端所有历史版本，可下载任意版本到本地
- ☁️ **云端为主** — 地图备份集中存储在 GitHub，本地只保留当前版本
- 🔄 **傻瓜操作** — 图形化界面，首次配置后一键同步

## 📦 下载

前往 [Releases](../../releases) 页面下载最新 `TerrariaMapSync.exe`，双击运行即可。

## 🚀 使用指南

### 准备工作

1. 安装 [Git](https://git-scm.com/download/win)
2. 配置 GitHub SSH 密钥（[教程](https://docs.github.com/zh/authentication/connecting-to-github-with-ssh)）
3. 让仓库所有者将你添加为仓库 [Collaborator](../../settings/access)

### 首次使用

1. 双击 `TerrariaMapSync.exe` 启动
2. 确认「地图文件夹」路径（通常自动识别）
3. 输入 GitHub 仓库地址，点击「克隆/更新」
4. 开始同步！

### 上传地图

1. 左侧列表选中要上传的地图
2. 点击「上传选中地图」
3. 确认后自动以 `YYYYMMDD+原名` 格式提交到云端

### 下载地图

1. 右侧树形列表展开地图，查看所有历史版本
2. 点击要下载的版本旁的「⬇ 下载」按钮
3. 云端文件自动去除日期前缀，覆盖本地同名旧文件

## 🛠️ 开发

```bash
conda create -n terraria-sync python=3.11
conda activate terraria-sync
pip install PySide6 GitPython
python main.py
```

打包：
```bash
pip install pyinstaller
pyinstaller --onefile --windowed --name TerrariaMapSync main.py
```

## 📄 许可

MIT License
