#!/usr/bin/env bash

set -euo pipefail

ROOT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
VENV_PYTHON="$ROOT_DIR/.venv/bin/python"
INSTALL_SCRIPT="$ROOT_DIR/scripts/install/linux_macos.sh"
PYTHON_BIN=""

log() {
    printf '[解放单手] %s\n' "$*"
}

python_is_compatible() {
    local candidate="$1"
    [[ -x "$candidate" ]] || return 1
    "$candidate" -c \
        'import sys, PyQt5; sys.platform != "darwin" or __import__("Quartz")' \
        >/dev/null 2>&1
}

consider_python() {
    local candidate="${1:-}"
    if [[ -z "$PYTHON_BIN" && -n "$candidate" ]] && python_is_compatible "$candidate"; then
        PYTHON_BIN="$candidate"
    fi
}

# 优先复用用户明确指定或当前已激活的 Conda/Python 环境。
consider_python "${HANDSFREE_PYTHON:-}"
if [[ -n "${CONDA_PREFIX:-}" ]]; then
    consider_python "$CONDA_PREFIX/bin/python"
fi
consider_python "$(command -v python3 2>/dev/null || true)"
consider_python "$VENV_PYTHON"

if [[ -z "$PYTHON_BIN" ]]; then
    bash "$INSTALL_SCRIPT"
    PYTHON_BIN="$VENV_PYTHON"
fi

if [[ "${1:-}" == "--show-python" ]]; then
    printf '%s\n' "$PYTHON_BIN"
    exit 0
fi

if [[ -n "${CONDA_PREFIX:-}" && "$PYTHON_BIN" == "$CONDA_PREFIX"/* ]]; then
    ENVIRONMENT_DESC="Conda：${CONDA_DEFAULT_ENV:-$CONDA_PREFIX}"
elif [[ "$PYTHON_BIN" == "$VENV_PYTHON" ]]; then
    ENVIRONMENT_DESC="项目本地 .venv"
else
    ENVIRONMENT_DESC="系统或自定义 Python"
fi

log "项目目录：$ROOT_DIR"
log "Python：$PYTHON_BIN"
log "运行环境：$ENVIRONMENT_DESC"
log "正在启动图形界面……"

"$PYTHON_BIN" "$ROOT_DIR/src/app.py" "$@" &
APP_PID=$!

stop_app() {
    trap - INT TERM
    log "收到退出信号，正在关闭程序（PID $APP_PID）……"
    kill "$APP_PID" 2>/dev/null || true
    wait "$APP_PID" 2>/dev/null || true
    log "程序已退出。"
    exit 130
}

trap stop_app INT TERM
sleep 1
if ! kill -0 "$APP_PID" 2>/dev/null; then
    if wait "$APP_PID"; then
        EXIT_CODE=0
    else
        EXIT_CODE=$?
    fi
    if [[ "$EXIT_CODE" -eq 0 ]]; then
        log "程序已正常结束，退出码：0"
    else
        log "启动失败，进程已提前退出，退出码：$EXIT_CODE"
    fi
    exit "$EXIT_CODE"
fi

log "启动成功，进程 PID：$APP_PID"
log "退出方式：关闭图形窗口，或在本终端按 Ctrl+C。"

if wait "$APP_PID"; then
    EXIT_CODE=0
else
    EXIT_CODE=$?
fi
trap - INT TERM
log "图形程序已结束，退出码：$EXIT_CODE"
exit "$EXIT_CODE"
