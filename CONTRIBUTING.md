# Contributing

感谢你改进“解放单手”。提交 Issue 或 Pull Request 前，请先确认问题仍能在最新 `main` 复现。

## 开发环境

```bash
python3 -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
```

Linux 无桌面测试可以使用 Qt 离屏模式：

```bash
QT_QPA_PLATFORM=offscreen .venv/bin/python -m unittest discover -s tests -v
```

## Pull Request 要求

- 一个 PR 聚焦一个问题，说明用户可见行为和验证方法。
- 修改调度、后端或 Herdr 状态处理时必须补测试。
- 修改用户流程、安装方式或平台能力时同步更新 `README.md` 和 `README.en.md`。
- 不提交 `.venv`、构建目录、录屏临时帧、终端日志、API 密钥或其他凭据。
- 后台输入属于高风险能力；无法确认目标或状态时，应优先停止而不是继续发送。

## 代码约定

- Python 使用类型标注，并保持平台相关实现位于 `src/handsfree/backends.py`。
- 调度逻辑保持可测试，不在工作线程直接操作 Qt 控件。
- 面向用户的错误信息应说明如何恢复，不静默吞掉会影响安全的错误。
- 文件编辑后运行 `git diff --check`，提交前运行完整测试。

## 报告问题

普通 Bug 请使用 GitHub Issue 模板，并包含操作系统、桌面会话（X11/Wayland）、终端、Herdr 版本、复现步骤和脱敏后的日志。安全问题不要开公开 Issue，请按 [SECURITY.md](SECURITY.md) 报告。
