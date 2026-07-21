#!/usr/bin/env bash

set -euo pipefail

INSTALL_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
ROOT_DIR="$(cd -- "$INSTALL_DIR/../.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"
LAUNCH_AFTER_INSTALL=0

if [[ "${1:-}" == "--launch" ]]; then
    LAUNCH_AFTER_INSTALL=1
fi

info() {
    printf '[解放单手] %s\n' "$*"
}

fail() {
    printf '[解放单手] 错误：%s\n' "$*" >&2
    exit 1
}

install_python_if_needed() {
    command -v python3 >/dev/null 2>&1 && return 0

    info "没有找到 Python 3，正在安装……"
    case "$(uname -s)" in
        Linux)
            if command -v apt-get >/dev/null 2>&1; then
                sudo apt-get update
                sudo apt-get install -y python3 python3-venv python3-pip
            elif command -v dnf >/dev/null 2>&1; then
                sudo dnf install -y python3 python3-pip
            elif command -v pacman >/dev/null 2>&1; then
                sudo pacman -Sy --needed python python-pip
            elif command -v zypper >/dev/null 2>&1; then
                sudo zypper install -y python3 python3-pip
            else
                fail "无法识别包管理器，请先安装 Python 3。"
            fi
            ;;
        Darwin)
            if command -v brew >/dev/null 2>&1; then
                brew install python
            else
                fail "请先安装 Homebrew 或从 python.org 安装 Python 3。"
            fi
            ;;
        *) fail "无法在当前系统自动安装 Python 3。" ;;
    esac
}

install_linux_dependencies() {
    command -v xdotool >/dev/null 2>&1 && return 0

    info "缺少 xdotool，正在安装系统依赖……"
    if command -v apt-get >/dev/null 2>&1; then
        sudo apt-get update
        sudo apt-get install -y xdotool python3-venv
    elif command -v dnf >/dev/null 2>&1; then
        sudo dnf install -y xdotool python3
    elif command -v pacman >/dev/null 2>&1; then
        sudo pacman -Sy --needed xdotool python
    elif command -v zypper >/dev/null 2>&1; then
        sudo zypper install -y xdotool python3
    else
        fail "无法识别包管理器，请先手工安装 xdotool 和 Python 3。"
    fi
}

create_linux_launcher() {
    local applications_dir desktop_file bin_dir bin_link
    applications_dir="${XDG_DATA_HOME:-$HOME/.local/share}/applications"
    desktop_file="$applications_dir/handsfree-enter.desktop"
    bin_dir="$HOME/.local/bin"
    bin_link="$bin_dir/handsfree-enter"

    mkdir -p "$applications_dir" "$bin_dir"
    printf '%s\n' \
        '[Desktop Entry]' \
        'Type=Application' \
        'Name=解放单手' \
        'Comment=多终端并行自动回车控制台' \
        "Exec=\"$ROOT_DIR/一键启动.sh\"" \
        'Icon=input-keyboard' \
        'Terminal=false' \
        'Categories=Utility;Development;' \
        > "$desktop_file"
    chmod +x "$desktop_file"
    ln -sfn "$ROOT_DIR/一键启动.sh" "$bin_link"
    info "已创建应用菜单入口和命令：handsfree-enter"
}

create_macos_launcher() {
    local applications_dir app_link
    applications_dir="$HOME/Applications"
    app_link="$applications_dir/解放单手.command"
    mkdir -p "$applications_dir"
    ln -sfn "$ROOT_DIR/一键启动.command" "$app_link"
    info "已创建：$app_link"
}

install_python_if_needed

case "$(uname -s)" in
    Linux) install_linux_dependencies ;;
    Darwin) ;;
    *) fail "此脚本用于 Linux/macOS；Windows 请双击“一键启动.bat”。" ;;
esac

info "正在创建独立 Python 环境……"
if [[ ! -x "$VENV_DIR/bin/python" ]]; then
    if ! python3 -m venv --system-site-packages "$VENV_DIR"; then
        if [[ "$(uname -s)" == "Linux" ]] && command -v apt-get >/dev/null 2>&1; then
            info "正在补装 python3-venv……"
            sudo apt-get update
            sudo apt-get install -y python3-venv
            python3 -m venv --system-site-packages "$VENV_DIR"
        else
            fail "无法创建虚拟环境，请安装 Python venv 支持后重试。"
        fi
    fi
fi

if ! "$VENV_DIR/bin/python" -c 'import PyQt5' >/dev/null 2>&1; then
    info "正在安装 Qt 界面依赖……"
    "$VENV_DIR/bin/python" -m pip install -r "$ROOT_DIR/requirements.txt"
fi

if [[ "$(uname -s)" == "Darwin" ]]; then
    if ! "$VENV_DIR/bin/python" -c 'import Quartz' >/dev/null 2>&1; then
        info "正在安装 macOS 后台窗口支持……"
        "$VENV_DIR/bin/python" -m pip install 'pyobjc-framework-Quartz>=10.0'
    fi
    create_macos_launcher
else
    create_linux_launcher
fi

chmod +x "$ROOT_DIR/一键启动.sh" "$ROOT_DIR/一键启动.command" \
    "$ROOT_DIR/scripts/install/linux_macos.sh" \
    "$ROOT_DIR/scripts/build/打包独立版.sh" \
    "$ROOT_DIR/scripts/build/制作跨电脑安装包.sh"

info "安装完成。"
if [[ "$LAUNCH_AFTER_INSTALL" -eq 1 ]]; then
    exec "$ROOT_DIR/一键启动.sh"
fi
