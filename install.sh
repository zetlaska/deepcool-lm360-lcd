#!/bin/bash
set -euo pipefail

readonly INSTALL_PREFIX="${INSTALL_PREFIX:-/usr/local}"
readonly BIN_DIR="${INSTALL_PREFIX}/bin"
readonly LIB_DIR="${INSTALL_PREFIX}/lib/lm360"
readonly SERVICE_DIR="/etc/systemd/system"
readonly SERVICE_NAME="lm360.service"
readonly LM360_GROUP="lm360"
readonly CONFLICTING_SERVICES=("deepcool-lm.service" "deepcool-lm-arkui.service")
readonly BACKUP_DIR="/var/backups/lm360-install-$(date +%Y%m%d-%H%M%S)"

log() {
    echo "[lm360-install] $*"
}

error() {
    echo "[lm360-install] ERROR: $*" >&2
    exit 1
}

detect_distro() {
    if [ -f /etc/os-release ]; then
        . /etc/os-release
        echo "${ID}"
    else
        echo "unknown"
    fi
}

check_usb_device() {
    if lsusb 2>/dev/null | grep -q "3633:0026"; then
        log "DeepCool LM360 USB device detected (3633:0026)"
        return 0
    else
        log "WARNING: DeepCool LM360 USB device (3633:0026) not detected"
        log "Install will continue, but the service will not function without the device"
        return 1
    fi
}

require_root() {
    if [ "$EUID" -ne 0 ]; then
        error "This operation requires root privileges. Run with sudo."
    fi
}

install_dependencies() {
    local distro="$1"
    local dry_run="${2:-false}"

    require_root

    log "Installing dependencies for distro: ${distro}"

    case "${distro}" in
        arch|manjaro|endeavouros|omarchy)
            local packages="python python-pyusb python-psutil python-pillow lm_sensors ttf-dejavu pciutils usbutils"
            if [ "${dry_run}" = "true" ]; then
                log "[DRY RUN] Would install: ${packages}"
            else
                pacman -S --needed --noconfirm ${packages}
            fi
            ;;
        debian|ubuntu|linuxmint|pop)
            local packages="python3 python3-usb python3-psutil python3-pil lm-sensors fonts-dejavu pciutils usbutils"
            if [ "${dry_run}" = "true" ]; then
                log "[DRY RUN] Would install: ${packages}"
            else
                apt-get update
                DEBIAN_FRONTEND=noninteractive apt-get install -y ${packages}
            fi
            ;;
        fedora|rhel|centos|rocky|almalinux)
            local packages="python3 python3-pyusb python3-psutil python3-pillow lm_sensors dejavu-sans-fonts pciutils usbutils"
            if [ "${dry_run}" = "true" ]; then
                log "[DRY RUN] Would install: ${packages}"
            else
                dnf install -y ${packages}
            fi
            ;;
        *)
            log "WARNING: Unsupported distribution '${distro}'"
            log "Please manually install: Python 3, PyUSB, psutil, Pillow, lm_sensors, DejaVu fonts, pciutils, usbutils"
            if [ "${dry_run}" != "true" ]; then
                read -p "Continue anyway? [y/N] " -n 1 -r
                echo
                if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                    exit 1
                fi
            fi
            ;;
    esac
}

create_group() {
    local dry_run="${1:-false}"

    require_root

    if [ "${dry_run}" = "true" ]; then
        log "[DRY RUN] Would create group: ${LM360_GROUP}"
        return
    fi

    if ! getent group "${LM360_GROUP}" >/dev/null 2>&1; then
        log "Creating group: ${LM360_GROUP}"
        groupadd -r "${LM360_GROUP}"
    else
        log "Group ${LM360_GROUP} already exists"
    fi
}

add_user_to_group() {
    local username="$1"
    local dry_run="${2:-false}"

    require_root

    if [ "${dry_run}" = "true" ]; then
        log "[DRY RUN] Would add user ${username} to group ${LM360_GROUP}"
        return
    fi

    if id "${username}" >/dev/null 2>&1; then
        log "Adding user ${username} to group ${LM360_GROUP}"
        usermod -a -G "${LM360_GROUP}" "${username}"
        log "User ${username} added to ${LM360_GROUP} group (relogin required)"
    fi
}

backup_existing_service() {
    local service="$1"
    local service_path="${SERVICE_DIR}/${service}"

    require_root

    if systemctl is-active --quiet "${service}"; then
        log "Stopping conflicting service: ${service}"
        systemctl stop "${service}" || true
    fi

    if systemctl is-enabled --quiet "${service}" 2>/dev/null; then
        log "Disabling conflicting service: ${service}"
        systemctl disable "${service}" || true
    fi

    if [ -f "${service_path}" ]; then
        mkdir -p "${BACKUP_DIR}"
        log "Backing up ${service} to ${BACKUP_DIR}/"
        cp -a "${service_path}" "${BACKUP_DIR}/"
    fi
}

check_conflicting_services() {
    require_root

    local found_conflict=false
    for service in "${CONFLICTING_SERVICES[@]}"; do
        if systemctl list-unit-files "${service}" 2>/dev/null | grep -q "${service}"; then
            log "Found conflicting service: ${service}"
            found_conflict=true
        fi
    done

    if [ "${found_conflict}" = "true" ]; then
        log "WARNING: Conflicting DeepCool services detected"
        log "These services will be stopped and disabled (backups saved to ${BACKUP_DIR})"
        log "This prevents dual USB ownership and ensures clean migration"
        read -p "Continue? [y/N] " -n 1 -r
        echo
        if [[ ! $REPLY =~ ^[Yy]$ ]]; then
            exit 1
        fi

        for service in "${CONFLICTING_SERVICES[@]}"; do
            if systemctl list-unit-files "${service}" 2>/dev/null | grep -q "${service}"; then
                backup_existing_service "${service}"
            fi
        done
    fi
}

install_files() {
    local dry_run="${1:-false}"

    require_root

    if [ "${dry_run}" = "true" ]; then
        log "[DRY RUN] Would create directories: ${BIN_DIR}, ${LIB_DIR}"
        log "[DRY RUN] Would install lm360 binary to ${BIN_DIR}/"
        log "[DRY RUN] Would install Python modules to ${LIB_DIR}/"
        log "[DRY RUN] Would install systemd service to ${SERVICE_DIR}/"
        return
    fi

    log "Creating installation directories"
    mkdir -p "${BIN_DIR}"
    mkdir -p "${LIB_DIR}"

    log "Installing lm360 binary"
    install -m 755 lm360-bin "${BIN_DIR}/lm360"

    log "Installing Python modules"
    cp -r lm360 "${LIB_DIR}/"
    find "${LIB_DIR}" -type f -name "*.py" -exec chmod 644 {} \;
    find "${LIB_DIR}" -type d -exec chmod 755 {} \;

    log "Installing systemd service"
    sed "s|/usr/local/bin/lm360|${BIN_DIR}/lm360|g" lm360.service > "${SERVICE_DIR}/${SERVICE_NAME}"
    chmod 644 "${SERVICE_DIR}/${SERVICE_NAME}"
}

setup_sensors() {
    if ! systemctl is-enabled --quiet lm_sensors.service 2>/dev/null; then
        log "NOTE: lm_sensors.service is not enabled"
        log "Temperature readings require lm_sensors to be configured"
        log "Run: sudo sensors-detect (answer YES to save config)"
        log "Then: sudo systemctl enable --now lm_sensors"
    fi
}

setup_service() {
    local dry_run="${1:-false}"
    local auto_enable="${2:-false}"

    require_root

    if [ "${dry_run}" = "true" ]; then
        log "[DRY RUN] Would reload systemd daemon"
        if [ "${auto_enable}" = "true" ]; then
            log "[DRY RUN] Would enable and start service"
        else
            log "[DRY RUN] Would NOT auto-enable service (manual enable required)"
        fi
        return
    fi

    log "Reloading systemd daemon"
    systemctl daemon-reload

    if [ "${auto_enable}" = "true" ]; then
        log "Enabling and starting service"
        systemctl enable --now "${SERVICE_NAME}"
        sleep 2
        systemctl status "${SERVICE_NAME}" --no-pager || true
    else
        log "Service installed but not enabled (manual start required)"
        log "To enable: sudo systemctl enable --now ${SERVICE_NAME}"
    fi
}

uninstall() {
    require_root

    log "Uninstalling lm360"

    if systemctl is-active --quiet "${SERVICE_NAME}"; then
        log "Stopping service"
        systemctl stop "${SERVICE_NAME}"
    fi

    if systemctl is-enabled --quiet "${SERVICE_NAME}" 2>/dev/null; then
        log "Disabling service"
        systemctl disable "${SERVICE_NAME}"
    fi

    log "Removing files"
    rm -f "${BIN_DIR}/lm360"
    rm -rf "${LIB_DIR}"
    rm -f "${SERVICE_DIR}/${SERVICE_NAME}"

    log "Reloading systemd"
    systemctl daemon-reload

    log "Uninstall complete"
    log "Group ${LM360_GROUP} preserved (remove manually if needed: groupdel ${LM360_GROUP})"
    log "State directory /var/lib/lm360 preserved"
}

main() {
    local command="${1:-install}"
    local dry_run=false
    local auto_enable=false

    if [ "${command}" = "--dry-run" ]; then
        dry_run=true
        command="install"
        log "DRY RUN MODE - no changes will be made"
    fi

    if [ "${command}" = "--enable" ]; then
        auto_enable=true
        command="install"
    fi

    if [ "${command}" = "uninstall" ]; then
        uninstall
        exit 0
    fi

    if [ "${command}" != "install" ]; then
        error "Usage: $0 [install|--enable|uninstall|--dry-run]"
    fi

    # Check if running as root for operations that need it
    local current_user="${SUDO_USER:-${USER}}"
    if [ "$EUID" -ne 0 ]; then
        log "Running as user ${current_user}"
        log "Some operations will require sudo (you may be prompted)"
        log ""
        log "Restarting with sudo..."
        exec sudo -E "$0" "$@"
    fi

    local distro
    distro=$(detect_distro)
    log "Detected distribution: ${distro}"

    if [ "${dry_run}" = "false" ]; then
        check_usb_device || true
        check_conflicting_services
    fi

    install_dependencies "${distro}" "${dry_run}"
    create_group "${dry_run}"
    
    if [ "${dry_run}" = "false" ] && [ -n "${current_user}" ] && [ "${current_user}" != "root" ]; then
        add_user_to_group "${current_user}" "${dry_run}"
    fi

    install_files "${dry_run}"

    if [ "${dry_run}" = "false" ]; then
        setup_sensors
    fi

    setup_service "${dry_run}" "${auto_enable}"

    if [ "${dry_run}" = "true" ]; then
        log "DRY RUN COMPLETE - no changes made"
    else
        log "Installation complete!"
        log ""
        log "IMPORTANT: Users must be in the '${LM360_GROUP}' group to use lm360 commands"
        log "User '${current_user}' has been added. Relogin or run: newgrp ${LM360_GROUP}"
        log ""
        log "Next steps:"
        log "  1. Relogin or run: newgrp ${LM360_GROUP}"
        log "  2. Configure lm_sensors: sudo sensors-detect"
        log "  3. Enable lm_sensors: sudo systemctl enable --now lm_sensors"
        if [ "${auto_enable}" = "false" ]; then
            log "  4. Start lm360: sudo systemctl enable --now ${SERVICE_NAME}"
        else
            log "  4. Service already started: systemctl status ${SERVICE_NAME}"
        fi
        log "  5. Test CLI: lm360 status"
        log "  6. View logs: sudo journalctl -u ${SERVICE_NAME} -f"
    fi
}

main "$@"
