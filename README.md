# VCP Auto Update Tool v1.0

<div align="center">

![VCP Auto Update Tool](https://img.shields.io/badge/VCP%20Auto%20Update%20Tool-v1.0-brightgreen?style=for-the-badge)

![Version](https://img.shields.io/badge/version-v1.0-blue.svg?style=flat-square)
![Python](https://img.shields.io/badge/python-3.7%2B-green.svg?style=flat-square)
![License](https://img.shields.io/badge/license-MIT-yellow.svg?style=flat-square)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20macOS-lightgrey.svg?style=flat-square)

**🚀 一键同步 VCP 项目，自动处理冲突，智能部署应用**

_让 VCP 项目更新变得简单、安全、高效_

[快速开始](#-快速开始) • [详细教程](#-详细教程) • [配置说明](#️-配置文件详解) • [常见问题](#-常见问题) • [故障排除](#-故障排除)

</div>

---

## ⚠️ 重要声明

本工具是社区开发的第三方自动化工具，用于帮助用户同步更新 Fork 的 VCP 项目。

**📢 使用须知**

- ✅ 本工具不是 VCP 项目的官方组件
- ✅ 使用前必须先 Fork 原始项目：[VCPChat](https://github.com/lioensky/VCPChat) 和 [VCPToolBox](https://github.com/lioensky/VCPToolBox)
- ✅ 本工具遵循 MIT 许可证，详见 `LICENSE` 文件
- ⚠️ **风险提示**：使用本工具的风险由用户自行承担
- 💡 **支持项目**：如果觉得有用，请给项目一个 ⭐ Star

---

## 📋 目录

- [🌟 什么是 VCP 自动更新工具](#-什么是-vcp-自动更新工具)
- [🎯 为什么需要这个工具](#-为什么需要这个工具)
- [💻 系统要求](#-系统要求)
- [🚀 快速开始](#-快速开始)
- [📚 详细教程](#-详细教程)
- [📁 脚本文件说明](#-脚本文件说明)
- [⚙️ 配置文件详解](#️-配置文件详解)
- [🔧 高级配置](#-高级配置)
- [❓ 常见问题](#-常见问题)
- [🆘 故障排除](#-故障排除)
- [📖 进阶使用](#-进阶使用)
- [🔒 安全性说明](#-安全性说明)
- [🤝 获取帮助](#-获取帮助)
- [📄 许可证](#-许可证)

---

## 🌟 什么是 VCP 自动更新工具

VCP 自动更新工具是一个智能化的自动化脚本系统，专为同步和部署 VCPChat 和 VCPToolBox 项目而设计。

### 🎯 核心功能

| 功能                 | 描述                                       |
| -------------------- | ------------------------------------------ |
| 🔄 **自动同步**      | 从原作者（lioensky）的仓库自动获取最新代码 |
| 🤖 **智能合并**      | 自动处理代码冲突，确保更新顺利进行         |
| 🐳 **Docker 自动化** | 自动重新构建和部署 VCPToolBox Docker 应用  |
| ⏪ **完整回滚**      | 提供多层次的回滚机制，更新失败可快速恢复   |
| 📊 **详细日志**      | 全程记录操作过程，便于问题诊断             |
| 🔒 **安全保护**      | 多重检查点保护，防止数据丢失               |

### 💡 技术特性

- **跨平台支持**：Windows、Linux、macOS 原生支持
- **并行处理**：支持并行更新多个项目，显著提升速度
- **健康检查**：Docker 容器自动健康检查和恢复
- **配置管理**：灵活的配置文件系统，支持个性化定制
- **网络优化**：内置重试机制和代理支持
- **模块化设计**：可独立使用各个功能模块

---

## 🎯 为什么需要这个工具

### ❌ 手动更新的痛点

当您 Fork 了 VCPChat 和 VCPToolBox 项目后，原作者会持续更新代码。手动同步这些更新极其繁琐：

- 需要手动添加和管理上游仓库
- 手动拉取、合并、解决冲突
- 手动推送到您的 Fork 仓库
- 手动重启和验证 Docker 服务
- 容易出错，耗时耗力
- 无法处理复杂的合并冲突
- 缺乏回滚和恢复机制

### ✅ 本工具的优势

- **一键完成**：所有步骤自动化，一个命令搞定
- **智能处理**：自动解决大部分合并冲突
- **安全可靠**：多重备份和检查点保护
- **实时监控**：Docker 健康检查和状态监控
- **详细日志**：完整的操作记录和错误诊断
- **灵活配置**：支持个性化设置和批量操作

---

## 💻 系统要求

### 📋 最低系统要求

| 组件         | 最低版本                                | 推荐版本                              | 说明                            |
| ------------ | --------------------------------------- | ------------------------------------- | ------------------------------- |
| **操作系统** | Windows 10 / Ubuntu 18.04 / macOS 10.14 | Windows 11 / Ubuntu 22.04 / macOS 13+ | 支持所有主流操作系统            |
| **Python**   | 3.7.0                                   | 3.9+                                  | 核心运行环境                    |
| **Git**      | 2.20.0                                  | 2.40+                                 | 版本控制系统                    |
| **Docker**   | 20.10.0                                 | 24.0+                                 | 容器运行环境（VCPToolBox 需要） |
| **内存**     | 2GB                                     | 4GB+                                  | 系统可用内存                    |
| **磁盘空间** | 1GB                                     | 5GB+                                  | 包含项目和日志存储              |
| **网络**     | 能访问 GitHub                           | 稳定的网络连接                        | 用于代码同步                    |

### 🔧 软件依赖详解

#### Python 环境

```bash
# 检查 Python 版本
python --version  # 或 python3 --version

# 必需的 Python 模块（通常已内置）
- json         # JSON 处理
- configparser # 配置文件解析
- subprocess   # 进程管理
- threading    # 多线程支持
- pathlib      # 路径处理
- dataclasses  # 数据类支持（Python 3.7+）
```

#### Git 配置

```bash
# 检查 Git 版本
git --version

# 基本配置（必需）
git config --global user.name "Your Name"
git config --global user.email "your.email@example.com"
```

#### Docker 环境（可选）

```bash
# 检查 Docker 版本
docker --version
docker-compose --version  # 或 docker compose version

# 确保 Docker 服务运行
sudo systemctl status docker  # Linux
# 或启动 Docker Desktop（Windows/macOS）
```

---

## 🚀 快速开始

> ⚠️ **重要提示**：请严格按照以下步骤执行，每个步骤都很重要！

### 📝 总体流程概览

```mermaid
graph LR
    A[1. Fork 原始仓库] --> B[2. 克隆到本地]
    B --> C[3. 下载更新工具]
    C --> D[4. 配置 Fork URL]
    D --> E[5. 运行自动更新]
```
```

### ✅ 环境准备检查清单

在开始之前，请确认以下环境已准备就绪：

- [ ] GitHub 账号已登录
- [ ] Python 3.7+ 已安装并配置 PATH
- [ ] Git 已安装并配置用户信息
- [ ] Docker 已安装（如需 VCPToolBox）
- [ ] 网络连接正常，可访问 GitHub
- [ ] 有足够的磁盘空间（至少 1GB）

---

## 📚 详细教程

### 步骤 1：Fork 原始仓库

> 💡 **什么是 Fork？** Fork 是在 GitHub 上创建一个仓库的个人副本，您可以自由修改而不影响原始仓库。

#### 1.1 Fork VCPChat 项目

1. **访问原始仓库**

   ```
   https://github.com/lioensky/VCPChat
   ```

2. **执行 Fork 操作**

   - 点击页面右上角的 **Fork** 按钮
   - 在弹出页面中配置：
     - Repository name: 保持默认 `VCPChat`
     - Description: 可选填写项目描述
     - ✅ 勾选 "Copy the main branch only"（推荐）
   - 点击 **Create fork**

3. **确认 Fork 成功**
   - 等待几秒钟，浏览器会重定向到您的 Fork
   - 确认 URL 格式为：`https://github.com/YOUR_USERNAME/VCPChat`

#### 1.2 Fork VCPToolBox 项目

1. **访问原始仓库**

   ```
   https://github.com/lioensky/VCPToolBox
   ```

2. **重复 Fork 流程**
   - 按照上述相同步骤操作
   - 确认 Fork 成功：`https://github.com/YOUR_USERNAME/VCPToolBox`

> ✅ **验证 Fork 成功**：确保您能访问以下两个 URL（将 YOUR_USERNAME 替换为您的实际用户名）：
>
> - `https://github.com/YOUR_USERNAME/VCPChat`
> - `https://github.com/YOUR_USERNAME/VCPToolBox`

### 步骤 2：克隆到本地

> 💡 **什么是克隆？** 克隆是将 GitHub 上的代码下载到您的电脑上，创建本地工作副本。

#### 2.1 创建项目目录结构

<details>
<summary><strong>🪟 Windows 操作步骤</strong></summary>

```cmd
# 打开命令提示符（Win+R，输入 cmd）
# 选择合适的驱动器（建议使用 D: 盘）
D:

# 创建 VCP 主目录
mkdir VCP
cd VCP

# 验证当前位置
echo %CD%
# 应显示：D:\VCP
```

</details>

<details>
<summary><strong>🐧 Linux/macOS 操作步骤</strong></summary>

```bash
# 创建项目目录
mkdir -p ~/VCP
cd ~/VCP

# 验证当前位置
pwd
# 应显示：/home/username/VCP 或 /Users/username/VCP
```

</details>

#### 2.2 克隆 Fork 仓库

<details>
<summary><strong>🪟 Windows 详细步骤</strong></summary>

```cmd
# 确保在 VCP 目录中
cd /d D:\VCP

# 克隆 VCPChat（替换 YOUR_USERNAME 为您的 GitHub 用户名）
git clone https://github.com/YOUR_USERNAME/VCPChat.git VCPChat

# 克隆 VCPToolBox
git clone https://github.com/YOUR_USERNAME/VCPToolBox.git VCPToolBox

# 验证克隆成功
dir
# 应该看到：
# VCPChat
# VCPToolBox
```

</details>

<details>
<summary><strong>🐧 Linux/macOS 详细步骤</strong></summary>

```bash
# 确保在 VCP 目录中
cd ~/VCP

# 克隆仓库（替换 YOUR_USERNAME）
git clone https://github.com/YOUR_USERNAME/VCPChat.git VCPChat
git clone https://github.com/YOUR_USERNAME/VCPToolBox.git VCPToolBox

# 验证克隆成功
ls -la
# 应该看到两个目录：VCPChat 和 VCPToolBox
```

</details>

### 步骤 3：下载并设置更新工具

#### 3.1 创建 VCPUpdate 目录

<details>
<summary><strong>🪟 Windows</strong></summary>

```cmd
# 在 VCP 主目录中创建 VCPUpdate
cd /d D:\VCP
mkdir VCPUpdate
cd VCPUpdate
```

</details>

<details>
<summary><strong>🐧 Linux/macOS</strong></summary>

```bash
# 在 VCP 主目录中创建 VCPUpdate
cd ~/VCP
mkdir VCPUpdate
cd VCPUpdate
```

</details>

#### 3.2 下载工具文件

您需要下载以下四个文件到 `VCPUpdate` 目录：

| 文件名           | 用途               | 平台        |
| ---------------- | ------------------ | ----------- |
| `update_vcp.py`  | Python 主脚本      | 所有平台    |
| `update_vcp.bat` | Windows 批处理文件 | Windows     |
| `update_vcp.sh`  | Shell 脚本         | Linux/macOS |
| `README.md`      | 使用说明文档       | 所有平台    |

**下载方法**：

1. **GitHub Release 下载**（推荐）

   - 访问项目的 Release 页面
   - 下载最新版本的压缩包
   - 解压到 VCPUpdate 目录

2. **手动创建文件**
   - 根据提供的文件内容创建对应文件
   - 确保文件编码为 UTF-8

#### 3.3 设置文件权限（Linux/macOS）

```bash
# 为脚本文件添加执行权限
chmod +x update_vcp.sh
chmod +x update_vcp.py
```

#### 3.4 验证目录结构

此时，您的目录结构应该是：

```
VCP/
├── VCPChat/               # VCPChat 项目
│   ├── .git/              # Git 仓库信息
│   ├── src/               # 源代码
│   └── ...                # 其他项目文件
├── VCPToolBox/            # VCPToolBox 项目
│   ├── .git/              # Git 仓库信息
│   ├── docker-compose.yml # Docker 配置
│   └── ...                # 其他项目文件
└── VCPUpdate/             # 更新工具目录
    ├── update_vcp.py      # Python 主脚本
    ├── update_vcp.bat     # Windows 脚本
    ├── update_vcp.sh      # Linux/macOS 脚本
    ├── README.md          # 说明文档
    ├── LICENSE            # MIT许可证文件
    └── .gitignore         # Git忽略文件
```

### 步骤 4：配置 Fork 仓库 URL

> ⚠️ **关键步骤**：这是新手最容易出错的地方，请仔细阅读！

#### 4.1 理解 Git 仓库关系

```mermaid
graph TD
    A[原作者仓库<br/>lioensky/VCPChat] -->|Fork| B[您的仓库<br/>YOUR_USERNAME/VCPChat]
    B -->|Clone| C[本地仓库<br/>VCPChat]
    A -->|获取更新| D[脚本自动处理]
    D -->|合并到| C
    C -->|推送到| B
```

#### 4.2 首次运行生成配置文件

<details>
<summary><strong>🪟 Windows</strong></summary>

```cmd
# 切换到 VCPUpdate 目录
cd /d D:\VCP\VCPUpdate

# 运行 Python 脚本生成配置文件
python update_vcp.py --action status
```

</details>

<details>
<summary><strong>🐧 Linux/macOS</strong></summary>

```bash
# 切换到 VCPUpdate 目录
cd ~/VCP/VCPUpdate

# 运行 Python 脚本生成配置文件
python3 update_vcp.py --action status
```

</details>

#### 4.3 编辑配置文件

运行上述命令后，会生成 `update_vcp_config.ini` 文件。使用文本编辑器打开此文件：

**找到 `[origins]` 部分**：

```ini
[origins]
VCPChat = https://github.com/YOUR_USERNAME/VCPChat.git
VCPToolBox = https://github.com/YOUR_USERNAME/VCPToolBox.git
```

**将 `YOUR_USERNAME` 替换为您的 GitHub 用户名**：

例如，如果您的 GitHub 用户名是 `john123`：

```ini
[origins]
VCPChat = https://github.com/john123/VCPChat.git
VCPToolBox = https://github.com/john123/VCPToolBox.git
```

#### 4.4 验证本地 Git 配置

确保本地仓库正确连接到您的 Fork：

<details>
<summary><strong>🪟 Windows</strong></summary>

```cmd
# 检查 VCPChat
cd /d D:\VCP\VCPChat
git remote -v

# 应该显示：
# origin  https://github.com/YOUR_USERNAME/VCPChat.git (fetch)
# origin  https://github.com/YOUR_USERNAME/VCPChat.git (push)

# 检查 VCPToolBox
cd /d D:\VCP\VCPToolBox
git remote -v
```

</details>

<details>
<summary><strong>🐧 Linux/macOS</strong></summary>

```bash
# 检查 VCPChat
cd ~/VCP/VCPChat
git remote -v

# 检查 VCPToolBox
cd ~/VCP/VCPToolBox
git remote -v
```

</details>

如果显示的不是您的仓库地址，需要修正（参见故障排除章节）。

### 步骤 5：运行自动更新

#### 5.1 启动更新工具

<details>
<summary><strong>🪟 Windows 用户</strong></summary>

```cmd
# 方法 1：双击批处理文件
# 直接双击 update_vcp.bat 文件

# 方法 2：命令行运行
cd /d D:\VCP\VCPUpdate
update_vcp.bat

# 方法 3：直接运行 Python 脚本
python update_vcp.py
```

</details>

<details>
<summary><strong>🐧 Linux/macOS 用户</strong></summary>

```bash
# 方法 1：运行 Shell 脚本
cd ~/VCP/VCPUpdate
./update_vcp.sh

# 方法 2：直接运行 Python 脚本
python3 update_vcp.py
```

</details>

#### 5.2 使用交互式菜单

工具启动后，您将看到一个交互式菜单：

```
============================================
         VCP Auto Update Tool v1.0
============================================

请选择操作：

更新选项:
  [1] 🚀 并行更新所有项目 (推荐)
  [2] 🔄 顺序更新所有项目
  [3] 📦 只更新 VCPChat
  [4] 🛠️  只更新 VCPToolBox

回滚选项:
  [5] ⏪ 回滚所有项目
  [6] ⏪ 回滚 VCPChat
  [7] ⏪ 回滚 VCPToolBox

管理选项:
  [S] ℹ️  查看项目状态
  [T] 🧪 环境检查
  [H] ❓ 显示帮助
  [0] 👋 退出

请输入选项:
```

#### 5.3 执行首次更新

**推荐步骤**：

1. **环境检查**：首次使用建议先选择 `[T]` 进行环境检查
2. **查看状态**：选择 `[S]` 查看项目当前状态
3. **执行更新**：选择 `[1]` 进行并行更新（推荐）

**更新过程说明**：

- 工具会自动创建备份和检查点
- 从上游仓库获取最新代码
- 智能合并代码变更
- 推送到您的 Fork 仓库
- 自动重新构建和部署 Docker 应用（如适用）
- 验证服务健康状态

---

## 📁 脚本文件说明

### 📄 update_vcp.py - Python 主脚本

**文件作用**：核心功能实现，跨平台通用的 Python 脚本

**主要功能**：

- 🔄 Git 操作自动化（克隆、拉取、合并、推送）
- 🐳 Docker 容器管理（构建、启动、健康检查）
- 📊 配置文件管理和验证
- 📝 详细日志记录和错误处理
- ⏪ 回滚和检查点管理
- 🔧 环境检测和依赖验证

**命令行用法**：

```bash
# 基本用法
python update_vcp.py

# 更新特定项目
python update_vcp.py --project chat
python update_vcp.py --project toolbox

# 执行特定操作
python update_vcp.py --action status
python update_vcp.py --action rollback
python update_vcp.py --action cleanup

# 调试模式
python update_vcp.py --debug

# 查看帮助
python update_vcp.py --help
```

**高级参数**：

| 参数            | 说明                               | 示例                     |
| --------------- | ---------------------------------- | ------------------------ |
| `--project`     | 指定项目（chat/toolbox）           | `--project chat`         |
| `--action`      | 执行操作（update/rollback/status） | `--action status`        |
| `--parallel`    | 并行模式（默认启用）               | `--parallel`             |
| `--sequential`  | 顺序模式                           | `--sequential`           |
| `--force-push`  | 强制推送                           | `--force-push`           |
| `--skip-docker` | 跳过 Docker 操作                   | `--skip-docker`          |
| `--debug`       | 启用调试模式                       | `--debug`                |
| `--config`      | 指定配置文件                       | `--config my_config.ini` |

### 📄 update_vcp.bat - Windows 批处理脚本

**文件作用**：Windows 平台的用户友好界面

**主要特性**：

- 🎨 彩色输出和交互式菜单
- 🔍 自动检测和验证 Python 环境
- 📋 详细的系统信息显示
- 🛠️ 内置故障排除和帮助信息
- 🔧 环境检查和配置验证

**使用方法**：

```cmd
# 直接双击运行
双击 update_vcp.bat

# 或在命令行中运行
cd /d D:\VCP\VCPUpdate
update_vcp.bat

# 调试模式运行
update_vcp.bat --debug
```

### 📄 update_vcp.sh - Linux/macOS Shell 脚本

**文件作用**：Unix 系统的原生脚本界面

**主要特性**：

- 🐧 支持 Linux 和 macOS 系统
- 🔒 严格的错误处理和安全检查
- 🔧 自动依赖检测和环境验证
- 📱 响应式终端界面
- 🌈 智能颜色支持检测

**使用方法**：

```bash
# 添加执行权限
chmod +x update_vcp.sh

# 运行脚本
./update_vcp.sh

# 调试模式
./update_vcp.sh --debug

# 安全模式
./update_vcp.sh --safe

# 无颜色模式
./update_vcp.sh --no-color
```

---

## ⚙️ 配置文件详解

### 📋 update_vcp_config.ini 结构

配置文件采用 INI 格式，包含以下主要部分：

```ini
# VCP Auto Update Configuration File
# Version: v1.0
# Generated: 2024-01-01 12:00:00

[general]       # 通用设置
[timeouts]      # 超时设置
[docker]        # Docker 相关设置
[performance]   # 性能优化设置
[logging]       # 日志配置
[network]       # 网络设置
[projects]      # 项目特定配置
[origins]       # Fork 仓库 URL
[custom_commands] # 自定义命令
```

### [general] - 通用设置

| 配置项                  | 默认值  | 说明                           | 可选值          |
| ----------------------- | ------- | ------------------------------ | --------------- |
| `auto_merge_conflicts`  | `true`  | 自动解决 Git 合并冲突          | `true`, `false` |
| `force_push`            | `false` | 启用强制推送模式               | `true`, `false` |
| `backup_before_update`  | `true`  | 更新前创建备份                 | `true`, `false` |
| `verify_docker_health`  | `true`  | 验证 Docker 容器健康状态       | `true`, `false` |
| `skip_unchanged_docker` | `true`  | 代码未变更时跳过 Docker 重建   | `true`, `false` |
| `create_restore_points` | `true`  | 创建 Git 检查点                | `true`, `false` |
| `max_backup_age_days`   | `30`    | 备份文件保留天数               | 数字（天）      |
| `auto_cleanup`          | `true`  | 自动清理旧文件                 | `true`, `false` |
| `interactive_mode`      | `false` | 启用交互确认模式               | `true`, `false` |
| `safe_merge_only`       | `false` | 安全合并模式（拒绝未提交更改） | `true`, `false` |

**配置示例**：

```ini
[general]
auto_merge_conflicts = true
force_push = false
backup_before_update = true
verify_docker_health = true
skip_unchanged_docker = true
interactive_mode = false
```

### [timeouts] - 超时设置

| 配置项                         | 默认值 | 说明                      | 范围    |
| ------------------------------ | ------ | ------------------------- | ------- |
| `git_timeout`                  | `180`  | Git 操作超时（秒）        | 30-3600 |
| `docker_timeout`               | `900`  | Docker 操作超时（秒）     | 60-3600 |
| `docker_health_check_timeout`  | `60`   | Docker 健康检查超时（秒） | 10-300  |
| `docker_health_check_interval` | `5`    | 健康检查间隔（秒）        | 1-30    |
| `network_retry_count`          | `3`    | 网络操作重试次数          | 1-10    |
| `network_retry_delay`          | `5`    | 重试间隔（秒）            | 1-60    |

**配置示例**：

```ini
[timeouts]
git_timeout = 180
docker_timeout = 900
network_retry_count = 3
```

### [docker] - Docker 设置

| 配置项                     | 默认值           | 说明                     | 可选值                                         |
| -------------------------- | ---------------- | ------------------------ | ---------------------------------------------- |
| `auto_prune`               | `false`          | 自动清理 Docker 资源     | `true`, `false`                                |
| `restart_policy`           | `unless-stopped` | 容器重启策略             | `no`, `on-failure`, `always`, `unless-stopped` |
| `max_restart_attempts`     | `3`              | 最大重启尝试次数         | 1-10                                           |
| `use_simple_health_check`  | `true`           | 使用简单健康检查         | `true`, `false`                                |
| `wait_before_health_check` | `10`             | 健康检查前等待时间（秒） | 5-60                                           |
| `rebuild_on_config_change` | `true`           | 配置变更时重建           | `true`, `false`                                |
| `remove_orphans`           | `true`           | 移除孤立容器             | `true`, `false`                                |

**配置示例**：

```ini
[docker]
auto_prune = false
restart_policy = unless-stopped
max_restart_attempts = 3
use_simple_health_check = true
```

### [performance] - 性能优化设置

| 配置项                   | 默认值  | 说明                   | 范围            |
| ------------------------ | ------- | ---------------------- | --------------- |
| `max_workers`            | `4`     | 并行处理最大工作线程数 | 1-16            |
| `enable_parallel_git`    | `true`  | 启用 Git 并行操作      | `true`, `false` |
| `enable_parallel_docker` | `false` | 启用 Docker 并行操作   | `true`, `false` |
| `batch_size`             | `10`    | 批处理大小             | 1-100           |

**配置示例**：

```ini
[performance]
max_workers = 4
enable_parallel_git = true
enable_parallel_docker = false
```

**性能调优建议**：

- **max_workers**：根据 CPU 核心数设置，通常为核心数的 1-2 倍
- **enable_parallel_docker**：谨慎启用，Docker 并行操作可能导致资源竞争
- 低配置机器建议设置 `max_workers = 2`

### [logging] - 日志配置

| 配置项                 | 默认值  | 说明               | 可选值                              |
| ---------------------- | ------- | ------------------ | ----------------------------------- |
| `log_level`            | `INFO`  | 日志级别           | `DEBUG`, `INFO`, `WARNING`, `ERROR` |
| `max_log_files`        | `30`    | 最大日志文件数     | 5-100                               |
| `log_rotation_size_mb` | `10`    | 日志轮转大小（MB） | 1-100                               |
| `enable_debug_logging` | `false` | 启用调试日志       | `true`, `false`                     |

**配置示例**：

```ini
[logging]
log_level = INFO
max_log_files = 30
enable_debug_logging = false
```

**日志级别说明**：

- **DEBUG**：详细的调试信息，包含所有操作细节
- **INFO**：一般信息，包含重要操作步骤
- **WARNING**：警告信息，可能的问题但不影响执行
- **ERROR**：错误信息，导致操作失败的问题

### [network] - 网络设置

| 配置项        | 默认值                | 说明             | 示例                 |
| ------------- | --------------------- | ---------------- | -------------------- |
| `use_proxy`   | `false`               | 启用代理         | `true`, `false`      |
| `http_proxy`  | ``                    | HTTP 代理地址    | `http://proxy:8080`  |
| `https_proxy` | ``                    | HTTPS 代理地址   | `https://proxy:8080` |
| `no_proxy`    | `localhost,127.0.0.1` | 不使用代理的地址 | 逗号分隔的地址列表   |
| `ssl_verify`  | `true`                | 启用 SSL 验证    | `true`, `false`      |

**代理配置示例**：

```ini
[network]
use_proxy = true
http_proxy = http://proxy.company.com:8080
https_proxy = http://proxy.company.com:8080
no_proxy = localhost,127.0.0.1,*.local
ssl_verify = true
```

### [projects] - 项目特定配置

此部分用于定义自定义项目配置，格式为 JSON：

```ini
[projects]
# 自定义项目配置示例
MyCustomProject = {
    "path": "MyProject",
    "upstream_url": "https://github.com/original/MyProject.git",
    "origin_url": "https://github.com/yourfork/MyProject.git",
    "has_docker": true,
    "docker_compose_file": "docker-compose.yml",
    "branch": "main",
    "auto_stash": true,
    "custom_commands": ["pre:echo 'Starting update'", "post:echo 'Update complete'"]
}
```

**项目配置参数说明**：

| 参数                  | 类型   | 说明                  | 示例                                     |
| --------------------- | ------ | --------------------- | ---------------------------------------- |
| `path`                | 字符串 | 项目本地路径          | `"MyProject"`                            |
| `upstream_url`        | 字符串 | 上游仓库 URL          | `"https://github.com/original/repo.git"` |
| `origin_url`          | 字符串 | Fork 仓库 URL         | `"https://github.com/yourfork/repo.git"` |
| `has_docker`          | 布尔值 | 是否包含 Docker       | `true`, `false`                          |
| `docker_compose_file` | 字符串 | Docker Compose 文件名 | `"docker-compose.yml"`                   |
| `branch`              | 字符串 | 主分支名称            | `"main"`, `"master"`                     |
| `auto_stash`          | 布尔值 | 自动暂存未提交更改    | `true`, `false`                          |
| `docker_port`         | 数字   | Docker 服务端口       | `3000`                                   |
| `docker_service_name` | 字符串 | Docker 服务名称       | `"myapp"`                                |

### [origins] - Fork 仓库 URL ⭐

**这是最重要的配置部分**，必须正确设置您的 Fork 仓库 URL：

```ini
[origins]
VCPChat = https://github.com/YOUR_USERNAME/VCPChat.git
VCPToolBox = https://github.com/YOUR_USERNAME/VCPToolBox.git
```

**重要说明**：

- 将 `YOUR_USERNAME` 替换为您的实际 GitHub 用户名
- URL 必须以 `.git` 结尾
- 确保仓库存在且可访问
- 支持 HTTPS 和 SSH 格式

**示例配置**：

```ini
[origins]
VCPChat = https://github.com/alice123/VCPChat.git
VCPToolBox = https://github.com/alice123/VCPToolBox.git

# 使用 SSH（需要配置 SSH 密钥）
# VCPChat = git@github.com:alice123/VCPChat.git
# VCPToolBox = git@github.com:alice123/VCPToolBox.git
```

### [custom_commands] - 自定义命令

支持在更新过程中执行自定义命令：

```ini
[custom_commands]
VCPChat = pre:echo "Starting VCPChat update",post:npm install
VCPToolBox = pre:docker system prune -f,post:echo "VCPToolBox updated"
```

**命令格式**：

- `pre:command` - 更新前执行
- `post:command` - 更新后执行
- 多个命令用逗号分隔
- 命令会在项目目录中执行

**安全注意事项**：

- 自定义命令具有较高权限，请谨慎使用
- 避免使用 `rm -rf`、`sudo` 等危险命令
- 工具会检测并拒绝已知的危险命令模式

---

## 🔧 高级配置

### 🌐 环境变量支持

工具支持通过环境变量覆盖配置：

```bash
# Windows
set VCP_LOG_LEVEL=DEBUG
set VCP_MAX_WORKERS=8
set VCP_ENABLE_PROXY=true

# Linux/macOS
export VCP_LOG_LEVEL=DEBUG
export VCP_MAX_WORKERS=8
export VCP_ENABLE_PROXY=true
```

### 📁 多配置文件管理

支持使用不同的配置文件：

```bash
# 使用自定义配置文件
python update_vcp.py --config production_config.ini
python update_vcp.py --config development_config.ini
```

### 🔧 Git 配置优化

在每个项目目录中，可以设置特定的 Git 配置：

```bash
# 进入项目目录
cd VCPChat

# 设置项目特定配置
git config user.name "Project Specific Name"
git config user.email "project@example.com"

# 设置代理（如果需要）
git config http.proxy http://proxy:8080
git config https.proxy http://proxy:8080

# 设置 SSL 选项
git config http.sslVerify false  # 仅在必要时使用
```

### 🐳 Docker 优化配置

对于 VCPToolBox 项目，可以优化 Docker 配置：

```yaml
# docker-compose.yml 优化示例
version: "3.8"
services:
  vcptoolbox:
    build:
      context: .
      dockerfile: Dockerfile
    restart: unless-stopped
    ports:
      - "3210:3210"
    environment:
      - NODE_ENV=production
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:3210/health"]
      interval: 30s
      timeout: 10s
      retries: 3
    logging:
      driver: "json-file"
      options:
        max-size: "10m"
        max-file: "3"
```

---

## ❓ 常见问题

### Q1: 为什么需要 Fork 而不是直接克隆原作者的仓库？

**A:** Fork 创建了您自己的副本，优势包括：

- ✅ 自由修改代码而不影响原作者
- ✅ 保存您的个人配置和修改
- ✅ 同时接收原作者的更新
- ✅ 向原作者提交 Pull Request 贡献代码
- ✅ 独立的版本控制和发布管理

### Q2: 如何知道我的 GitHub 用户名？

**A:** 获取用户名的方法：

1. 登录 GitHub 后，点击右上角头像
2. 用户名显示在头像下方
3. 查看浏览器地址栏：`https://github.com/YOUR_USERNAME`
4. 命令行查看：`git config user.name`

### Q3: 配置文件在哪里？如何重新生成？

**A:** 配置文件位置和管理：

- **Windows**: `D:\VCP\VCPUpdate\update_vcp_config.ini`
- **Linux/macOS**: `~/VCP/VCPUpdate/update_vcp_config.ini`

**重新生成方法**：

```bash
# 删除现有配置文件
rm update_vcp_config.ini  # Linux/macOS
del update_vcp_config.ini  # Windows

# 重新运行脚本生成新配置
python update_vcp.py --action status
```

### Q4: 更新失败了怎么办？

**A:** 故障排除步骤：

**1. 查看错误信息**

```bash
# 查看最新日志
ls -la update_vcp_logs/  # Linux/macOS
dir update_vcp_logs\     # Windows
```

**2. 使用回滚功能**

```bash
# 回滚所有项目
python update_vcp.py --action rollback

# 回滚特定项目
python update_vcp.py --action rollback --project chat
```

**3. 运行环境检查**

```bash
# 全面环境检查
python update_vcp.py --action status
```

**4. 启用调试模式**

```bash
# 调试模式执行
python update_vcp.py --debug
```

### Q5: 需要每次都输入 GitHub 密码吗？

**A:** 不需要，有多种免密方法：

**方法 1：使用个人访问令牌（推荐）**

1. 访问 https://github.com/settings/tokens
2. 点击 "Generate new token (classic)"
3. 选择权限：✅ repo（完整仓库访问）
4. 生成令牌并复制
5. 第一次推送时使用令牌作为密码
6. 配置 Git 保存凭据：

```bash
git config --global credential.helper store
```

**方法 2：配置 SSH 密钥**

```bash
# 生成 SSH 密钥
ssh-keygen -t ed25519 -C "your.email@example.com"

# 添加到 SSH agent
ssh-add ~/.ssh/id_ed25519

# 将公钥添加到 GitHub
cat ~/.ssh/id_ed25519.pub
# 复制输出内容到 GitHub SSH Keys 设置
```

### Q6: 可以自定义更新时间吗？

**A:** 可以，有多种方式：

**手动执行**

```bash
# 随时手动运行
python update_vcp.py
```

**Windows 任务计划程序**

1. 创建批处理文件 `auto_update.bat`：

```batch
@echo off
cd /d D:\VCP\VCPUpdate
python update_vcp.py --project all
```

2. 在任务计划程序中设置定时运行

**Linux/macOS Cron 任务**

```bash
# 编辑 crontab
crontab -e

# 每天凌晨 2 点自动更新
0 2 * * * cd ~/VCP/VCPUpdate && python3 update_vcp.py --project all

# 每周日凌晨 3 点更新
0 3 * * 0 cd ~/VCP/VCPUpdate && python3 update_vcp.py --project all
```

### Q7: Docker 是必需的吗？

**A:** 不是必需的，依情况而定：

- **VCPChat**: 不需要 Docker，纯代码项目
- **VCPToolBox**: 通常需要 Docker 运行服务
- 可以在配置文件中设置 `verify_docker_health = false` 跳过 Docker 检查

### Q8: 如何处理合并冲突？

**A:** 工具提供多种冲突处理策略：

**自动处理（默认）**

```ini
[general]
auto_merge_conflicts = true  # 自动解决冲突，使用上游版本
```

**手动处理**

```ini
[general]
auto_merge_conflicts = false  # 禁用自动合并，需手动解决
```

**安全模式**

```ini
[general]
safe_merge_only = true  # 拒绝有未提交更改的操作
```

### Q9: 支持哪些 Git 远程仓库格式？

**A:** 支持多种格式：

```ini
[origins]
# HTTPS 格式（推荐）
VCPChat = https://github.com/username/VCPChat.git

# SSH 格式
VCPChat = git@github.com:username/VCPChat.git

# 企业 GitHub
VCPChat = https://github.enterprise.com/username/VCPChat.git

# 其他 Git 服务
VCPChat = https://gitlab.com/username/VCPChat.git
```

### Q10: 如何备份和恢复配置？

**A:** 配置管理最佳实践：

**备份配置**

```bash
# 备份配置文件
cp update_vcp_config.ini update_vcp_config.backup

# 导出配置模板
python update_vcp.py --action export-config
```

**恢复配置**

```bash
# 从备份恢复
cp update_vcp_config.backup update_vcp_config.ini

# 验证配置
python update_vcp.py --action status
```

---

## 🆘 故障排除

### ❌ 错误：未配置 Fork 仓库 URL

**错误信息**：

```
❌ 错误: 未配置Fork仓库URL，请在配置文件[origins]部分设置VCPChat的URL
```

**解决方案**：

**步骤 1：编辑配置文件**

```bash
# 找到配置文件
# Windows: D:\VCP\VCPUpdate\update_vcp_config.ini
# Linux/macOS: ~/VCP/VCPUpdate/update_vcp_config.ini
```

**步骤 2：修改 [origins] 部分**

```ini
[origins]
VCPChat = https://github.com/YOUR_REAL_USERNAME/VCPChat.git
VCPToolBox = https://github.com/YOUR_REAL_USERNAME/VCPToolBox.git
```

**步骤 3：验证 GitHub 用户名**

- 登录 GitHub 查看个人资料页面
- 确认仓库确实存在且可访问

### ❌ 错误：Python 版本过低

**错误信息**：

```
Python版本过低: 3.6.x
需要Python 3.7或更高版本
```

**解决方案**：

**Windows 用户**

1. 访问 https://www.python.org/downloads/
2. 下载 Python 3.9+ 版本
3. 安装时务必勾选 "Add Python to PATH"
4. 重启命令提示符验证：`python --version`

**Linux 用户**

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install python3.9 python3.9-pip

# CentOS/RHEL
sudo yum install python39 python39-pip

# 创建软链接
sudo ln -sf /usr/bin/python3.9 /usr/bin/python3
```

**macOS 用户**

```bash
# 使用 Homebrew
brew install python@3.9

# 或下载官方安装包
# https://www.python.org/downloads/macos/
```

### ❌ 错误：Git 连接超时

**错误信息**：

```
fatal: unable to access 'https://github.com/...': Connection timed out
```

**解决方案**：

**方法 1：检查网络连接**

```bash
# 测试 GitHub 连通性
ping github.com
curl -I https://github.com

# 测试 DNS 解析
nslookup github.com
```

**方法 2：配置代理（公司网络）**

```bash
# 设置 Git 代理
git config --global http.proxy http://proxy:port
git config --global https.proxy http://proxy:port

# 或在配置文件中设置
```

```ini
[network]
use_proxy = true
http_proxy = http://proxy.company.com:8080
https_proxy = http://proxy.company.com:8080
```

**方法 3：使用 SSH 代替 HTTPS**

```bash
# 生成 SSH 密钥
ssh-keygen -t ed25519 -C "your.email@example.com"

# 修改仓库 URL 为 SSH 格式
git remote set-url origin git@github.com:username/repo.git
```

**方法 4：调整 Git 配置**

```bash
# 增加超时时间
git config --global http.timeout 300

# 设置更大的缓冲区
git config --global http.postBuffer 524288000

# 使用 HTTP/1.1
git config --global http.version HTTP/1.1
```

### ❌ 错误：Docker 服务未运行

**错误信息**：

```
❌ Docker服务未运行 - 请启动Docker Desktop
```

**解决方案**：

**Windows 用户**

1. 启动 Docker Desktop 应用程序
2. 等待 Docker 完全启动（状态显示为绿色）
3. 验证：`docker --version`

**Linux 用户**

```bash
# 启动 Docker 服务
sudo systemctl start docker

# 设置开机自启
sudo systemctl enable docker

# 添加用户到 docker 组
sudo usermod -aG docker $USER

# 重新登录或执行
newgrp docker

# 验证
docker run hello-world
```

**macOS 用户**

1. 启动 Docker Desktop 应用
2. 确保 Docker 图标在菜单栏显示为运行状态
3. 验证：`docker --version`

### ❌ 错误：合并冲突

**错误信息**：

```
检测到合并冲突，尝试自动解决...
自动解决失败，需要手动处理
```

**解决方案**：

**方法 1：启用自动冲突解决**

```ini
[general]
auto_merge_conflicts = true
```

**方法 2：手动解决冲突**

```bash
# 进入项目目录
cd VCPChat

# 查看冲突文件
git status

# 编辑冲突文件，解决冲突标记
# <<<<<<< HEAD
# 您的更改
# =======
# 上游更改
# >>>>>>> upstream/main

# 标记冲突已解决
git add .
git commit -m "Resolve merge conflicts"
```

**方法 3：使用回滚功能**

```bash
# 如果冲突复杂，直接回滚
python update_vcp.py --action rollback --project chat
```

### ❌ 错误：权限被拒绝

**错误信息**：

```
Permission denied (publickey)
或
fatal: Authentication failed
```

**解决方案**：

**HTTPS 认证问题**

1. 使用个人访问令牌：

   - 访问 https://github.com/settings/tokens
   - 生成新令牌，选择 repo 权限
   - 使用令牌作为密码

2. 配置凭据存储：

```bash
git config --global credential.helper store
```

**SSH 认证问题**

1. 检查 SSH 密钥：

```bash
ls -la ~/.ssh/
```

2. 生成新 SSH 密钥：

```bash
ssh-keygen -t ed25519 -C "your.email@example.com"
```

3. 添加公钥到 GitHub：

```bash
cat ~/.ssh/id_ed25519.pub
# 复制输出到 GitHub SSH Keys 设置
```

4. 测试 SSH 连接：

```bash
ssh -T git@github.com
```

### ❌ 错误：磁盘空间不足

**错误信息**：

```
No space left on device
或
Disk quota exceeded
```

**解决方案**：

**清理磁盘空间**

```bash
# 清理 Git 仓库
git gc --aggressive --prune=now

# 清理 Docker 资源
docker system prune -a -f

# 清理工具日志和备份
python update_vcp.py --action cleanup
```

**检查磁盘使用**

```bash
# Linux/macOS
df -h
du -sh VCP/

# Windows
dir VCP /s
```

### 🌐 网络相关问题

**DNS 解析问题**

```bash
# 更换 DNS 服务器
# Windows: 控制面板 > 网络 > 更改适配器设置
# Linux: /etc/resolv.conf
# macOS: 系统偏好设置 > 网络 > 高级 > DNS

# 临时使用公共 DNS
echo "nameserver 8.8.8.8" > /etc/resolv.conf  # Linux
```

**防火墙问题**

```bash
# 临时关闭防火墙测试
sudo ufw disable  # Ubuntu
sudo systemctl stop firewalld  # CentOS

# Windows: 控制面板 > 系统和安全 > Windows Defender 防火墙
```

---

## 📖 进阶使用

### ⚡ 并行 vs 顺序更新

**并行更新（推荐）**

- ✅ 速度快，同时处理多个项目
- ✅ 适合网络状况良好的环境
- ⚠️ 可能增加系统负载

```bash
python update_vcp.py --parallel
```

**顺序更新**

- ✅ 系统负载低，稳定可靠
- ✅ 便于调试问题
- ⚠️ 总耗时较长

```bash
python update_vcp.py --sequential
```

### 🔄 Git 检查点系统

工具自动创建多个检查点，提供精细的回滚控制：

**检查点类型**

- `before_update` - 更新前的状态
- `after_remote_setup` - 设置远程仓库后
- `after_fetch` - 获取上游代码后
- `after_merge` - 合并代码后
- `after_push` - 推送完成后

**检查点操作**

```bash
# 查看所有检查点
python update_vcp.py --action list-checkpoints

# 恢复到特定检查点
python update_vcp.py --action checkpoint --project chat --checkpoint before_update
```

### 🛠️ 自定义项目支持

除了 VCPChat 和 VCPToolBox，还可以添加自定义项目：

```ini
[projects]
MyProject = {
    "path": "MyProject",
    "upstream_url": "https://github.com/original/MyProject.git",
    "origin_url": "https://github.com/yourfork/MyProject.git",
    "has_docker": true,
    "docker_compose_file": "docker-compose.yml",
    "branch": "main"
}
```

### 💻 高级命令行用法

```bash
# 组合多个参数
python update_vcp.py --project chat --force-push --debug

# 跳过 Docker 操作
python update_vcp.py --skip-docker

# 安全模式（拒绝未提交更改）
python update_vcp.py --safe-mode

# 使用自定义配置文件
python update_vcp.py --config production.ini
```

### 📦 批量操作脚本

创建批量操作脚本：

**Windows (batch_update.bat)**

```batch
@echo off
echo 开始批量更新...

cd /d D:\VCP\VCPUpdate
python update_vcp.py --project chat
if %errorlevel% neq 0 goto error

python update_vcp.py --project toolbox
if %errorlevel% neq 0 goto error

echo 批量更新完成！
goto end

:error
echo 更新失败，开始回滚...
python update_vcp.py --action rollback

:end
pause
```

**Linux/macOS (batch_update.sh)**

```bash
#!/bin/bash
set -e

echo "开始批量更新..."

cd ~/VCP/VCPUpdate

# 更新项目
python3 update_vcp.py --project chat || {
    echo "VCPChat 更新失败，开始回滚..."
    python3 update_vcp.py --action rollback --project chat
    exit 1
}

python3 update_vcp.py --project toolbox || {
    echo "VCPToolBox 更新失败，开始回滚..."
    python3 update_vcp.py --action rollback --project toolbox
    exit 1
}

echo "批量更新完成！"
```

### 📊 监控和通知

集成监控和通知功能：

**邮件通知脚本**

```python
import smtplib
from email.mime.text import MIMEText
import subprocess
import sys

def send_notification(status, message):
    # 配置邮件服务器
    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    email = "your-email@gmail.com"
    password = "your-app-password"

    msg = MIMEText(f"VCP 更新状态: {status}\n\n{message}")
    msg['Subject'] = f"VCP 更新通知 - {status}"
    msg['From'] = email
    msg['To'] = email

    try:
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()
        server.login(email, password)
        server.send_message(msg)
        server.quit()
        print("通知邮件已发送")
    except Exception as e:
        print(f"发送邮件失败: {e}")

# 执行更新
result = subprocess.run([sys.executable, "update_vcp.py"],
                       capture_output=True, text=True)

if result.returncode == 0:
    send_notification("成功", "所有项目更新完成")
else:
    send_notification("失败", f"更新失败:\n{result.stderr}")
```

### ⚙️ 性能优化

**系统资源优化**

```ini
[performance]
# 低配置机器设置
max_workers = 2
enable_parallel_git = true
enable_parallel_docker = false

# 高配置机器设置
max_workers = 8
enable_parallel_git = true
enable_parallel_docker = true
```

**网络优化**

```ini
[timeouts]
# 网络较慢时调整超时
git_timeout = 300
network_retry_count = 5
network_retry_delay = 10
```

**Docker 优化**

```ini
[docker]
# 启用资源清理
auto_prune = true
use_simple_health_check = true
wait_before_health_check = 15
```

---

## 🔒 安全性说明

### 🛡️ 数据保护

**备份机制**

- 🔒 更新前自动创建 Git bundle 备份
- 🔒 多层检查点保护，可精确回滚
- 🔒 配置文件自动备份
- 🔒 日志文件加密存储（可选）

**权限控制**

- 🔒 最小权限原则，只访问必要的文件
- 🔒 自定义命令安全检查，拒绝危险操作
- 🔒 网络访问限制，仅连接授权的 Git 仓库
- 🔒 临时文件安全清理

**敏感信息保护**

```ini
# 配置文件中避免明文存储敏感信息
[network]
# ❌ 错误：明文存储密码
# http_proxy = http://user:password@proxy:8080

# ✅ 正确：使用环境变量或凭据管理器
http_proxy = http://proxy:8080
```

**推荐安全实践**

1. **使用个人访问令牌**而非密码
2. **配置 SSH 密钥**进行免密认证
3. **定期轮换**访问令牌和密钥
4. **启用二因素认证**（2FA）
5. **定期检查**授权应用和令牌

### 🌐 网络安全

**HTTPS 强制**

```bash
# 强制使用 HTTPS
git config --global url."https://".insteadOf git://
```

**证书验证**

```ini
[network]
ssl_verify = true  # 始终启用 SSL 验证
```

**代理安全**

```ini
[network]
# 只在受信任的网络环境中使用代理
use_proxy = false
# 配置可信的代理服务器
http_proxy = http://trusted-proxy.company.com:8080
```

### 🔐 代码完整性

**签名验证**

```bash
# 启用 Git 提交签名验证
git config --global commit.gpgsign true
git config --global tag.gpgsign true
```

**哈希检验**

- 工具自动验证下载文件的完整性
- 检查 Git 提交的 SHA 值
- 监控异常的文件变更

### 🔒 隐私保护

**日志脱敏**

- 自动移除日志中的敏感信息
- 加密存储包含凭据的日志
- 定期清理过期日志文件

**匿名使用**

```ini
[logging]
# 禁用详细日志以保护隐私
enable_debug_logging = false
log_level = WARNING
```

---

## 🤝 获取帮助

### 📚 官方资源

**项目主页**

- 📋 **VCPChat**: https://github.com/lioensky/VCPChat
- 🛠️ **VCPToolBox**: https://github.com/lioensky/VCPToolBox
- 📖 **更新工具文档**: 本 README 文件

**社区支持**

- 💬 **GitHub Issues**: 报告 Bug 和功能请求
- 📧 **邮件支持**: 通过项目维护者联系
- 📱 **社交媒体**: 关注项目动态

### 📝 问题报告指南

当遇到问题时，请提供以下信息：

**基本信息**

```bash
# 收集系统信息
python update_vcp.py --action status > system_info.txt

# 收集环境信息
python --version
git --version
docker --version  # 如果适用

# 操作系统信息
# Windows: systeminfo
# Linux: uname -a && lsb_release -a
# macOS: sw_vers
```

**日志信息**

```bash
# 最新日志文件位置
ls -la update_vcp_logs/

# 错误日志（如果有）
grep -i error update_vcp_logs/*.log
```

**配置信息**

```bash
# 脱敏后的配置文件
cat update_vcp_config.ini | grep -v -E "(password|token|key)"
```

### ✅ 故障排除检查清单

在寻求帮助前，请先检查：

**环境检查**

- [ ] Python 版本 >= 3.7
- [ ] Git 已安装且配置用户信息
- [ ] 网络连接正常，可访问 GitHub
- [ ] 磁盘空间充足（>1GB）
- [ ] Docker 服务运行正常（如需要）

**配置检查**

- [ ] Fork 仓库 URL 配置正确
- [ ] GitHub 用户名拼写无误
- [ ] 本地 Git 仓库连接到正确的远程仓库
- [ ] 访问令牌或 SSH 密钥配置有效

**权限检查**

- [ ] 对项目目录有读写权限
- [ ] Git 凭据配置正确
- [ ] Docker 用户权限足够（如需要）

**网络检查**

- [ ] 可以 ping 通 github.com
- [ ] 防火墙未阻止 Git 操作
- [ ] 代理配置正确（如使用代理）

### 🔧 自助诊断工具

**运行完整诊断**

```bash
# 全面环境检查
python update_vcp.py --action status

# 调试模式运行
python update_vcp.py --debug

# 网络连接测试
ping github.com
curl -I https://github.com
```

**常见修复命令**

```bash
# 重置 Git 配置
git config --global --unset http.proxy
git config --global --unset https.proxy

# 清理 Git 缓存
git config --global --unset credential.helper
git credential-manager-core erase

# 重新生成配置文件
rm update_vcp_config.ini
python update_vcp.py --action status
```

### 🤝 贡献指南

欢迎为项目贡献代码和文档：

**贡献类型**

- 🐛 **Bug 修复**: 修复现有问题
- ✨ **新功能**: 添加有用的功能
- 📚 **文档**: 改进文档和说明
- 🧪 **测试**: 添加测试用例
- 🎨 **优化**: 性能优化和代码重构

**贡献流程**

1. Fork 本项目仓库
2. 创建功能分支：`git checkout -b feature/amazing-feature`
3. 提交更改：`git commit -m 'Add some AmazingFeature'`
4. 推送分支：`git push origin feature/amazing-feature`
5. 创建 Pull Request

**代码规范**

- 使用 Python PEP 8 代码风格
- 添加适当的注释和文档字符串
- 确保所有测试通过
- 更新相关文档

---

## 🎯 最佳实践总结

### 📅 日常使用建议

**定期更新策略**

- 🕐 **每周更新**: 建议每周至少执行一次更新
- 🔍 **更新前检查**: 运行状态检查确认环境正常
- 📊 **查看日志**: 更新后检查日志确认成功
- 💾 **验证功能**: 更新后测试关键功能是否正常

**备份策略**

- 📦 **保留备份**: 不要立即删除旧备份文件
- 🏷️ **版本标记**: 为重要版本创建手动标签
- 💿 **外部备份**: 定期将重要配置备份到外部存储

**监控策略**

- 📈 **性能监控**: 定期检查 Docker 容器资源使用
- 🚨 **错误监控**: 设置自动化监控脚本
- 📱 **通知机制**: 配置更新状态通知

### 👥 团队协作建议

**配置标准化**

```ini
# 团队共享的基础配置模板
[general]
auto_merge_conflicts = true
backup_before_update = true
verify_docker_health = true

[timeouts]
git_timeout = 180
docker_timeout = 900

[performance]
max_workers = 4
enable_parallel_git = true
```

**版本控制**

- 🏷️ 使用统一的版本标记策略
- 📋 维护更新日志和变更记录
- 🔄 定期同步团队配置

**文档维护**

- 📚 维护团队专用的配置文档
- 🎓 提供新成员培训材料
- 🔄 及时更新最佳实践指南

### 🚀 生产环境部署

**环境分离**

```bash
# 开发环境配置
cp update_vcp_config.ini config_dev.ini

# 生产环境配置
cp update_vcp_config.ini config_prod.ini

# 使用特定配置
python update_vcp.py --config config_prod.ini
```

**自动化部署**

```bash
#!/bin/bash
# 生产环境自动更新脚本

set -e

# 环境检查
python3 update_vcp.py --action status --config config_prod.ini

# 执行更新
python3 update_vcp.py --config config_prod.ini

# 健康检查
sleep 30
python3 update_vcp.py --action status --config config_prod.ini

echo "生产环境更新完成"
```

**回滚预案**

```bash
#!/bin/bash
# 紧急回滚脚本

echo "执行紧急回滚..."
python3 update_vcp.py --action rollback --config config_prod.ini

echo "验证回滚结果..."
python3 update_vcp.py --action status --config config_prod.ini
```

---

## 🚀 未来发展路线图

### 📅 计划中的功能

**v1.1 版本**

- 🔧 图形用户界面（GUI）
- 📊 更详细的统计报告
- 🔄 增量更新优化
- 🌐 多语言支持
- ☁️ 云端配置同步
- 🤖 智能冲突解决
- 📱 移动端监控应用
- 🔗 Webhook 集成
- 🐋 Kubernetes 支持
- 🔄 微服务架构
- 🛡️ 企业级安全功能
- 📈 高级分析仪表板

### 👥 社区参与

我们欢迎社区的参与和贡献：

- 💡 **功能建议**: 提出新功能想法
- 🐛 **Bug 报告**: 帮助发现和修复问题
- 📝 **文档改进**: 改善文档质量
- 🌍 **国际化**: 提供多语言翻译
- 🧪 **测试支持**: 帮助测试新功能

---

## 📄 许可证

本项目采用 MIT 许可证，详情请参见 LICENSE 文件。

### 第三方组件

本工具使用了以下开源组件：

- **Python**: Python Software Foundation License
- **Git**: GNU General Public License v2.0
- **Docker**: Apache License 2.0

### 免责声明

- 本工具仅供学习和开发使用
- 使用前请确保遵守相关法律法规和项目许可证
- 作者不承担因使用本工具而导致的任何损失
- 请在测试环境中充分验证后再用于生产环境
- 对原 VCP 项目的使用请遵循其原始许可证条款

### 贡献

欢迎提交 Issue 和 Pull Request 来改进本工具！

---

<div align="center">

### 🌟 如果这个工具对您有帮助，请给个 ⭐ Star！

**让 VCP 项目更新变得简单、安全、高效**

---

**感谢您的使用和支持！**

_最后更新时间: 2025 年 7 月_

[返回顶部](#vcp-auto-update-tool-v10)

</div>
