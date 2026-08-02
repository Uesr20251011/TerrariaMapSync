# 🗺️ 泰拉瑞亚联机地图同步助手

通过 GitHub 仓库实现多人联机地图同步。谁开服谁上传，其他人下载最新地图，再也不用手动传文件。

## ✨ 功能

- 🔍 自动识别本地泰拉瑞亚地图，无需手动找文件夹
- 📤 一键上传，自动添加时间戳（精确到秒），不覆盖历史版本
- 📥 自由下载任意历史版本到本地，自动附带备份文件（.wld.bak / .wld.bak2）
- 📋 三栏清晰展示：地图名、时间、操作
- ☁️ GitHub 云端存储，本地只保留当前使用的地图
- 📝 操作日志完整记录，遇到问题一键导出

---

## 🚀 准备工作（首次使用前必读）

### 第一步：下载安装 Git

Git 是本工具运行所必需的，负责与 GitHub 仓库通信。

1. 打开 https://git-scm.com/download/win
2. 下载后双击安装，**一路点 Next 用默认设置即可**
3. 安装完成后验证：按 `Win+R`，输入 `cmd` 回车，在黑色窗口输入：
   ```
   git --version
   ```
   如果显示 `git version 2.xx.xx` 就说明装好了。

### 第二步：注册 GitHub 账号并配置 SSH

1. 打开 https://github.com 注册一个账号（免费的，用邮箱注册即可）
2. 注册完成后，配置 SSH 密钥（让 Git 能免密操作你的仓库）：
   - 按 `Win+R`，输入 `cmd` 回车
   - 在黑色窗口输入以下命令（把邮箱换成你的 GitHub 注册邮箱）：
     ```
     ssh-keygen -t ed25519 -C "your-email@example.com"
     ```
     一路按回车，不要设密码。
   - 然后输入：
     ```
     cat %userprofile%\.ssh\id_ed25519.pub
     ```
   - 会输出一串 `ssh-ed25519` 开头的内容，**全选复制**
3. 打开 GitHub 网站 → 右上角头像 → **Settings** → 左侧 **SSH and GPG keys** → 绿色 **New SSH key**
4. Title 随便填（比如"我的电脑"），Key 里粘贴刚才复制的内容，点 **Add SSH key**

> 更详细的 SSH 配置教程可参考：[GitHub 官方教程](https://docs.github.com/zh/authentication/connecting-to-github-with-ssh)

### 第三步：安装 GitHub CLI 并登录

1. 打开 https://cli.github.com 下载 GitHub CLI 安装
2. 安装完成后，按 `Win+R`，输入 `powershell` 回车
3. 输入以下命令并回车：
   ```
   gh auth login
   ```
4. 依次选择：
   - `GitHub.com`
   - `HTTPS`
   - `Login with a web browser`
5. 浏览器会自动打开，点绿色按钮授权即可

---

## 👥 多人协作设置（仓库所有者操作）

### 创建地图存储仓库

1. 登录你的 GitHub，点击右上角 `+` → **New repository**
2. Repository name 填 `TerrariaMaps`
3. 选 **Private**（私有，只有你和协作者能访问）
4. 勾选 "Add a README file"
5. 点 **Create repository**

### 添加协作者（朋友们）

1. 进入刚创建的仓库页面 → **Settings** → 左侧 **Collaborators**
2. 点 **Add people**，输入朋友的 GitHub 用户名
3. 朋友会收到邀请邮件，接受后即可访问仓库

### 把仓库地址发给朋友

仓库地址格式：`https://github.com/你的用户名/TerrariaMaps.git`

例如：`https://github.com/Uesr20251011/TerrariaMaps.git`

---

## 📦 下载工具

前往 [Releases](../../releases) 页面下载最新的 `TerrariaMapSync.exe`。

**就一个文件**，双击运行，无需安装。

---

## 📖 使用指南

### 首次启动

1. 双击 `TerrariaMapSync.exe`
2. 顶部「地图文件夹」通常已自动识别（你的 `Documents\My Games\Terraria\Worlds`）
3. 在「仓库地址」输入仓库所有者给你的地址（如 `https://github.com/Uesr20251011/TerrariaMaps.git`）
4. 点击「克隆/更新」按钮，等待完成
5. 左侧出现你的本地地图，右侧云端暂无（第一次使用时）

### 上传地图

1. 左侧列表**点击**选中要上传的地图
2. 点击「⬆ 上传选中地图」
3. 确认对话框会显示云端文件名（如 `20260802173025我的世界.wld`）
4. 确认后等待上传完成

### 下载地图

1. 右侧云端面板展开地图名
2. 查看各版本的时间（如 `2026年08月02日 17:30:25`）
3. 点击对应版本的「⬇ 下载」
4. 云端文件会自动去时间戳，覆盖本地同名旧文件
5. 备份文件（.wld.bak / .wld.bak2）会一并下载

### 更新云端列表

点击「克隆/更新」按钮刷新云端仓库，或点击右侧「🔄 刷新」。

---

## 🐛 遇到问题？

工具底部有 **📋 导出日志** 按钮。点击后保存日志文件，发给作者排查。

日志也保存在：`C:\Users\你的用户名\AppData\Roaming\TerrariaMapHelper\logs\`

---

## ⚠️ 注意事项

- **关闭泰拉瑞亚再操作**：游戏运行时地图文件被锁定，无法读写
- **git push 需要仓库写入权限**：确保仓库所有者已将你添加为 Collaborator
- **同一天多次上传不会覆盖**：文件名精确到秒（`YYYYMMDDHHMMSS`），每次上传都是独立版本

---

## 📄 许可

MIT License
