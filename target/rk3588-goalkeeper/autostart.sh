#!/bin/bash
# ============================================================
# 足球检测开机自启动管理脚本（香橙派 RK3588）
#
# 首次使用（在香橙派上，本仓库目录下执行）:
#   chmod +x autostart.sh
#   ./autostart.sh install     # 安装 systemd 服务并开启开机自启
#
# 日常使用:
#   ./autostart.sh status      # 查看：自启是开还是关 + 程序是否在运行
#   ./autostart.sh on          # 开启开机自启
#   ./autostart.sh off         # 关闭开机自启
#   ./autostart.sh start       # 立即启动程序（不改变自启设置）
#   ./autostart.sh stop        # 立即停止程序（不改变自启设置）
#   ./autostart.sh restart     # 立即重启程序
#   ./autostart.sh log         # 实时查看程序日志（Ctrl+C 退出）
#   ./autostart.sh uninstall   # 彻底移除服务
# ============================================================

SERVICE=c5-goalkeeper
ENV_NAME=yolov8   # conda 环境名
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
UNIT_SRC="$SCRIPT_DIR/deploy/$SERVICE.service"
UNIT_DST="/etc/systemd/system/$SERVICE.service"

installed() { [ -f "$UNIT_DST" ]; }

require_installed() {
    if ! installed; then
        echo "✗ 服务尚未安装，请先执行: ./autostart.sh install"
        exit 1
    fi
}

show_status() {
    if ! installed; then
        echo "开机自启: ✗ 未安装（执行 ./autostart.sh install 安装）"
        return
    fi
    enabled=$(systemctl is-enabled "$SERVICE" 2>/dev/null)
    active=$(systemctl is-active "$SERVICE" 2>/dev/null)

    if [ "$enabled" = "enabled" ]; then
        echo "开机自启: ✓ 已开启"
    else
        echo "开机自启: ✗ 已关闭 ($enabled)"
    fi
    if [ "$active" = "active" ]; then
        echo "当前程序: ✓ 运行中"
    else
        echo "当前程序: ✗ 未运行 ($active)"
    fi
    echo "──────────────────────────────"
    systemctl status "$SERVICE" --no-pager -n 5 2>/dev/null | head -20
}

case "$1" in
    install)
        if [ ! -f "$UNIT_SRC" ]; then
            echo "✗ 找不到 $UNIT_SRC"
            exit 1
        fi
        # 路径含空格/特殊字符会破坏 sed 替换和 ExecStart，直接拒绝
        case "$SCRIPT_DIR" in
            *[[:space:]]*|*'|'*|*'&'*|*'\'*)
                echo "✗ 仓库路径含空格或特殊字符: $SCRIPT_DIR"
                echo "  请把仓库移到普通路径（如 /home/orangepi/c5-car-playground）后重试"
                exit 1
                ;;
        esac
        # 检查 main.py 引用的模型文件是否存在，避免装出一个开机就崩溃循环的服务
        model=$(sed -n 's/^MODEL_PATH = "\.\/\(.*\)"$/\1/p' "$SCRIPT_DIR/main.py")
        if [ -n "$model" ] && [ ! -f "$SCRIPT_DIR/$model" ]; then
            echo "✗ 模型文件不存在: $SCRIPT_DIR/$model"
            echo "  请先把模型放进 rknnModel/ 目录再安装"
            exit 1
        fi
        # 定位 conda 环境 yolov8 的 python
        # （systemd 不能执行 conda activate，直接用环境内 python 绝对路径，效果等价）
        PY=""
        if command -v conda >/dev/null 2>&1; then
            base=$(conda info --base 2>/dev/null)
            if [ -n "$base" ] && [ -x "$base/envs/$ENV_NAME/bin/python3" ]; then
                PY="$base/envs/$ENV_NAME/bin/python3"
            fi
        fi
        if [ -z "$PY" ]; then
            for d in "$HOME/miniconda3" "$HOME/anaconda3" "$HOME/miniforge3" "$HOME/mambaforge" \
                     /home/orangepi/miniconda3 /home/orangepi/anaconda3 /home/orangepi/miniforge3; do
                if [ -x "$d/envs/$ENV_NAME/bin/python3" ]; then
                    PY="$d/envs/$ENV_NAME/bin/python3"
                    break
                fi
            done
        fi
        if [ -z "$PY" ]; then
            echo "⚠ 未找到 conda 环境 $ENV_NAME 的 python，暂用系统 python3"
            echo "  如需修改，安装后编辑 $UNIT_DST 的 ExecStart 行"
            PY="/usr/bin/python3"
        else
            echo "✓ 使用 conda 环境 python: $PY"
        fi
        # 先在临时文件生成 unit（修正仓库路径 + python 路径），成功后再安装，
        # 避免中途失败在 /etc/systemd/system 留下空文件/半截文件
        tmp=$(mktemp) || exit 1
        sed -e "s|/home/orangepi/c5-car-playground/target/rk3588-goalkeeper|$SCRIPT_DIR|g" \
            -e "s|^ExecStart=.*|ExecStart=$PY $SCRIPT_DIR/main.py|" \
            "$UNIT_SRC" > "$tmp" || { rm -f "$tmp"; echo "✗ 生成 unit 文件失败"; exit 1; }
        sudo install -m 644 "$tmp" "$UNIT_DST" || { rm -f "$tmp"; echo "✗ 写入 $UNIT_DST 失败"; exit 1; }
        rm -f "$tmp"
        sudo systemctl daemon-reload || { echo "✗ daemon-reload 失败"; exit 1; }
        sudo systemctl enable "$SERVICE" || { echo "✗ 开启自启失败"; exit 1; }
        echo "✓ 安装完成，开机自启已开启（重启后自动运行 main.py）"
        echo "  现在就启动: ./autostart.sh start"
        ;;
    status)
        show_status
        ;;
    on)
        require_installed
        sudo systemctl enable "$SERVICE" && echo "✓ 开机自启已开启" || { echo "✗ 操作失败"; exit 1; }
        ;;
    off)
        require_installed
        sudo systemctl disable "$SERVICE" && echo "✓ 开机自启已关闭（当前运行中的程序不受影响）" || { echo "✗ 操作失败"; exit 1; }
        ;;
    start)
        require_installed
        sudo systemctl start "$SERVICE" || { echo "✗ 启动失败"; exit 1; }
        sleep 1
        show_status
        ;;
    stop)
        require_installed
        sudo systemctl stop "$SERVICE" && echo "✓ 程序已停止" || { echo "✗ 停止失败"; exit 1; }
        ;;
    restart)
        require_installed
        sudo systemctl restart "$SERVICE" || { echo "✗ 重启失败"; exit 1; }
        sleep 1
        show_status
        ;;
    log)
        require_installed
        journalctl -u "$SERVICE" -f --no-pager
        ;;
    uninstall)
        require_installed
        sudo systemctl disable --now "$SERVICE" 2>/dev/null
        sudo rm -f "$UNIT_DST"
        sudo systemctl daemon-reload
        echo "✓ 服务已彻底移除"
        ;;
    *)
        echo "用法: ./autostart.sh {install|status|on|off|start|stop|restart|log|uninstall}"
        echo ""
        echo "  install    首次安装并开启开机自启"
        echo "  status     查看自启开/关状态 + 程序运行状态"
        echo "  on / off   开启 / 关闭开机自启"
        echo "  start/stop 立即启动 / 停止程序（不影响自启设置）"
        echo "  restart    立即重启程序"
        echo "  log        实时查看日志"
        echo "  uninstall  彻底移除服务"
        exit 1
        ;;
esac
