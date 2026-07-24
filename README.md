# 解放单手

“解放单手”是一个面向 Codex、Claude Code 等终端 AI Agent 的多任务自动回车控制台。它可以给每个任务锁定独立目标、按指定间隔发送 Enter，并在 Herdr 报告 AI 任务完成后自动停止，避免任务结束后继续发送回车而误提交正在输入的内容。

本仓库只维护一个版本：包含 Herdr 定向发送与状态监控能力的完整版本。普通终端窗口仍可使用，但在 Linux 上配合 [Herdr](https://herdr.dev/) 能获得更可靠的定向发送和自动停止体验。

## 为什么推荐配合 Herdr

普通终端模式依赖操作系统提供的窗口标识和键盘注入能力，无法可靠判断 Codex 或 Claude Code 是否已经完成。Herdr 为每个 Agent 提供独立 Pane、稳定的 Pane ID 和结构化的 `agent_status`，因此本工具可以：

- 从 Pane 列表直接选择 Codex 或 Claude Code，不会选错外层终端窗口；
- 通过 `herdr pane send-keys <pane> enter` 定向发送，不要求 Pane 位于前台；
- 通过 `herdr pane get <pane>` 读取 `working`、`blocked`、`idle` 状态；
- 在状态变为 `idle` 时自动停止，发送前再做一次强制状态检查；
- 在 Linux Wayland 下绕过普通窗口禁止后台按键注入的限制。

Herdr 不是强制依赖：没有安装 Herdr 时，程序仍可锁定普通终端窗口并按次数、时长或手动规则运行。

## 功能

- Herdr Pane 定向发送，支持 Codex、Claude Code 和普通 Pane；
- AI 任务完成后自动停止，状态无法确认时安全停止；
- 可视化调整全局状态检查间隔，范围 `0.5～10 秒`，默认 `1 秒`；
- 普通终端窗口保护锁，任务运行时不会跟随鼠标或活动窗口改变目标；
- 多个终端或 Pane 同时运行独立任务；
- 支持按一次或循环发送，第一次回车前等待一个完整间隔；
- 循环任务支持手动停止、总次数、总时长和 AI 完成自动停止；
- 每个任务可停止、重新运行、修改设置、更换目标或删除；
- 一键停止全部任务；
- Qt 原生界面，高 DPI、系统中文字体和跨平台缩放；
- Linux、macOS、Windows 安装与启动脚本。

## 推荐安装方式：Linux + Herdr

先按照 [Herdr 官方安装文档](https://herdr.dev/docs/install/) 安装并启动 Herdr。官方提供的稳定版安装命令是：

```bash
curl -fsSL https://herdr.dev/install.sh | sh
herdr
```

然后安装“解放单手”：

```bash
git clone https://github.com/XiangQhello/handsfree-enter.git
cd handsfree-enter
chmod +x 一键启动.sh
./一键启动.sh
```

启动器会优先复用当前带有 PyQt5 的 Conda/Python 环境；找不到兼容环境时，才会创建一次本地 `.venv`。也可以显式指定解释器：

```bash
HANDSFREE_PYTHON=/路径/到/python ./一键启动.sh
```

首次运行需要能够在 `PATH` 中找到 `herdr`。程序也会检查 `~/.local/bin/herdr`。

## Herdr 使用流程

1. 在 Herdr 中启动 Codex 或 Claude Code。
2. 打开“解放单手”，点击“选择 Herdr AI Agent / Pane”。
3. 从列表中选择具体 Pane，而不是点击外层 GNOME Terminal 窗口。
4. 选择“循环发送”，设置回车间隔。
5. 停止条件选择“AI 任务完成后自动停止（推荐）”。
6. 点击“添加并启动任务”。

状态处理规则：

| Herdr 状态 | 行为 |
|---|---|
| `working` | AI 正在工作，继续监控 |
| `blocked` | AI 正在等待确认或输入，继续按计划运行 |
| `idle` | 本轮任务已结束，立即停止且不再发送 |
| 无法查询或未知状态 | 异常停止，不盲目发送 |

“AI 状态检查间隔（全局）”只控制 Pane 状态轮询频率，不改变回车发送间隔。修改后会作用于运行中的自动停止任务；无论轮询间隔多长，每次真正发送回车前都会额外检查一次状态。

## 普通终端模式

点击“选择普通终端窗口”，再用鼠标选择目标窗口。每张任务卡保存固定的原生窗口标识，不会因为你点击其他终端、浏览器或编辑器而改变目标。

普通终端模式无法读取 AI Agent 状态，因此只提供手动停止、总次数和总时长。请为它设置保守的停止条件，不要在自动回车仍运行时向目标终端输入半条命令。

## 其他平台启动方式

### macOS

在 Finder 中双击“一键启动.command”。首次发送前，需要在“系统设置 → 隐私与安全性 → 辅助功能”中授权。

### Windows

双击“一键启动.bat”。电脑需要 Python 3；安装程序会创建本地环境和桌面快捷方式。

## 平台能力

| 平台 | Herdr 定向发送 | 普通终端后台发送 | 说明 |
|---|---|---|---|
| Linux + Herdr | 支持 | X11 支持 | 推荐组合；Wayland 下也可使用 Herdr Pane |
| Linux X11/Xorg | 不需要 Herdr | 支持 | 短暂改变键盘焦点，不抬起窗口 |
| Linux Wayland | 支持 | 不支持 | Wayland 禁止向任意普通窗口注入按键 |
| Windows | 尚未接入 | 实验支持 | 终端需接受 Win32 后台窗口消息 |
| macOS | 尚未接入 | 实验支持 | 需要辅助功能权限，按进程投递 |

Windows Terminal 等特殊输入架构可能拒绝后台 Win32 消息；macOS 同一终端应用的多个窗口也可能由同一进程管理。这些限制来自操作系统和终端实现。

## 开发与测试

```bash
python -m unittest discover -s tests -v
```

目录结构：

```text
解放单手/
├── 一键启动.sh / .command / .bat   三个平台的用户入口
├── src/                             程序源码
│   └── handsfree/managed_workspace.py  Herdr CLI/API 集成
├── scripts/install/                 安装脚本
├── scripts/build/                   打包脚本
├── tests/                           自动测试
├── requirements.txt                 Python 依赖
├── VERSION                          版本号
└── README.md                        使用说明
```

生成跨电脑安装包：

```bash
./scripts/build/制作跨电脑安装包.sh
```

输出文件为上一级目录中的 `解放单手-版本号.zip`。生成无需 Python 的独立版本时，Linux/macOS 运行 `./scripts/build/打包独立版.sh`，Windows 使用 `scripts/build/打包独立版.ps1`。

## Herdr 引用与第三方说明

本项目通过 Herdr CLI/API 使用 Pane 列表、定向按键和 Agent 状态能力，不包含或修改 Herdr 源码。Herdr 是独立的开源项目：

- 官网：[herdr.dev](https://herdr.dev/)
- 文档：[herdr.dev/docs](https://herdr.dev/docs/)
- 源码：[ogulcancelik/herdr](https://github.com/ogulcancelik/herdr)
- 许可证：[Apache License 2.0](https://github.com/ogulcancelik/herdr/blob/master/LICENSE)

Codex、Claude Code、Herdr 及其名称和商标分别归各自权利人所有。本仓库与这些项目的维护者不存在官方隶属或背书关系。

## 安全提醒

自动回车会确认目标终端当时显示的内容。即使使用 AI 完成自动停止，也不要用它自动批准删除、覆盖、发布或其他需要人工判断的危险操作。对于无法读取状态的普通终端，应优先限制总次数或总时长。
