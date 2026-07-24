# 第三方声明 / Third-Party Notices

本仓库不复制或修改以下上游项目的源码。运行时依赖和外部工具继续适用各自的许可证、商标与使用条款。

## PyQt5

- 用途：图形界面与 Qt 事件循环
- 项目：[Riverbank Computing — PyQt](https://www.riverbankcomputing.com/software/pyqt/)
- 许可证：[GNU GPL v3 或商业许可证](https://www.riverbankcomputing.com/commercial/license-faq)

本项目采用 GPL v3，与 PyQt5 GPL v3 兼容。若使用 Riverbank 商业许可证重新分发，应由发布者自行确认适用条款。

## Qt

- 用途：由 PyQt5 调用的跨平台 GUI 库
- 项目：[Qt](https://www.qt.io/)
- 许可证说明：[Qt Licensing](https://www.qt.io/licensing/)

具体 Qt 二进制的许可证取决于安装来源。仓库本身不提交 Qt 二进制。

## Herdr

- 用途：可选的 Pane 枚举、定向按键和 AI Agent 状态查询
- 官网：[herdr.dev](https://herdr.dev/)
- 源码：[ogulcancelik/herdr](https://github.com/ogulcancelik/herdr)
- 许可证：[Apache License 2.0](https://github.com/ogulcancelik/herdr/blob/master/LICENSE)

Herdr 是独立进程，本项目只通过其公开 CLI/API 与之通信，不捆绑 Herdr 二进制或源码。

## PyObjC

- 用途：macOS Quartz 后台键盘事件支持，仅在 macOS 安装
- 项目：[PyObjC](https://pyobjc.readthedocs.io/)
- 源码：[ronaldoussoren/pyobjc](https://github.com/ronaldoussoren/pyobjc)

## xdotool

- 用途：Linux X11 普通终端窗口选择与键盘输入
- 源码：[jordansissel/xdotool](https://github.com/jordansissel/xdotool)

`xdotool` 是系统级外部命令，不包含在本仓库或源码安装包中。

Codex、Claude Code、Herdr、PyQt、Qt 及其名称和商标分别归各自权利人所有。引用这些名称只用于说明兼容性和集成关系，不表示官方隶属或背书。
