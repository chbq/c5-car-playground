#!/bin/bash
# Install and explicitly gate the autonomous goalkeeper motion service.

set -u

SERVICE=c5-goalkeeper-motion
DRY_SERVICE=c5-goalkeeper
TOKEN=I_ACCEPT_AUTONOMOUS_MOTION
GATE=/etc/c5-goalkeeper-motion.enable
ENV_NAME=yolov8
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
UNIT_SRC="$SCRIPT_DIR/deploy/$SERVICE.service"
UNIT_DST="/etc/systemd/system/$SERVICE.service"

require_installed() {
    if [ ! -f "$UNIT_DST" ]; then
        echo "✗ 运动服务尚未安装"
        exit 1
    fi
}

require_token() {
    if [ "${2:-}" != "$TOKEN" ]; then
        echo "✗ 需要明确确认口令: $TOKEN"
        exit 1
    fi
}

find_python() {
    for d in "$HOME/miniconda3" "$HOME/anaconda3" "$HOME/miniforge3" \
             /home/orangepi/miniconda3 /home/orangepi/anaconda3; do
        if [ -x "$d/envs/$ENV_NAME/bin/python3" ]; then
            echo "$d/envs/$ENV_NAME/bin/python3"
            return
        fi
    done
    echo /usr/bin/python3
}

resolve_host() {
    local py host
    py=$(find_python)
    host=$(PYTHONPATH="$SCRIPT_DIR${PYTHONPATH:+:$PYTHONPATH}" \
        "$py" -c 'from serial_transport import resolve_serial_port; print(resolve_serial_port())') \
        || return 1
    [ -e "$host" ] || return 1
    printf '%s\n' "$host"
}

case "${1:-}" in
    install)
        case "$SCRIPT_DIR" in
            *[[:space:]]*|*'|'*|*'&'*|*'\'*)
                echo "✗ 路径含空格或特殊字符: $SCRIPT_DIR"
                exit 1
                ;;
        esac
        model=$(sed -n 's/^MODEL_PATH = "\.\/\(.*\)"$/\1/p' "$SCRIPT_DIR/main.py")
        if [ -z "$model" ] || [ ! -f "$SCRIPT_DIR/$model" ]; then
            echo "✗ 模型不存在: $SCRIPT_DIR/$model"
            exit 1
        fi
        py=$(find_python)
        tmp=$(mktemp) || exit 1
        sed -e "s|/home/orangepi/c5-car-playground/target/rk3588-goalkeeper|$SCRIPT_DIR|g" \
            -e "s|/home/orangepi/miniconda3/envs/yolov8/bin/python3|$py|g" \
            "$UNIT_SRC" > "$tmp" || { rm -f "$tmp"; exit 1; }
        sudo install -m 644 "$tmp" "$UNIT_DST" || { rm -f "$tmp"; exit 1; }
        rm -f "$tmp"
        sudo systemctl daemon-reload
        sudo systemctl disable "$SERVICE" >/dev/null 2>&1 || true
        sudo rm -f "$GATE"
        echo "✓ 运动服务已安装但未启用；未 ARM、未动车"
        ;;
    enable-next-boot)
        require_installed
        require_token "$@"
        if ! host=$(resolve_host 2>/dev/null); then
            echo "✗ 未找到唯一 C5 HOST 串口；多串口时需设置 C5_HOST_PORT"
            exit 1
        fi
        echo "✓ C5 HOST 候选: $host"
        sudo systemctl disable --now "$DRY_SERVICE" >/dev/null 2>&1 || true
        printf 'explicitly enabled\n' | sudo tee "$GATE" >/dev/null
        sudo chmod 600 "$GATE"
        sudo systemctl enable "$SERVICE"
        echo "✓ 已允许下次开机自动运动；当前未启动"
        ;;
    start)
        require_installed
        require_token "$@"
        if [ ! -f "$GATE" ]; then
            echo "✗ 运动使能文件不存在；先执行 enable-next-boot"
            exit 1
        fi
        sudo systemctl start "$SERVICE"
        ;;
    disable-now)
        require_installed
        sudo systemctl disable --now "$SERVICE" >/dev/null 2>&1 || true
        sudo rm -f "$GATE"
        echo "✓ 已停止并撤销自动运动授权"
        ;;
    status)
        printf "installed="; [ -f "$UNIT_DST" ] && echo yes || echo no
        printf "gate="; [ -f "$GATE" ] && echo present || echo absent
        printf "enabled="; systemctl is-enabled "$SERVICE" 2>/dev/null || true
        printf "active="; systemctl is-active "$SERVICE" 2>/dev/null || true
        ;;
    *)
        echo "用法: ./motion_autostart.sh {install|status|disable-now}"
        echo "危险操作需口令:"
        echo "  ./motion_autostart.sh enable-next-boot $TOKEN"
        echo "  ./motion_autostart.sh start $TOKEN"
        exit 1
        ;;
esac
