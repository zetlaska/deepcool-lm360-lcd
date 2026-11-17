#!/bin/bash
# Emergency repair script for lm360 packaging bug
# Fixes ModuleNotFoundError by correcting nested directory structure

set -euo pipefail

readonly LIB_DIR="/usr/local/lib/lm360"
readonly SERVICE_NAME="lm360.service"

log() {
    echo "[lm360-repair] $*"
}

error() {
    echo "[lm360-repair] ERROR: $*" >&2
    exit 1
}

require_root() {
    if [ "$EUID" -ne 0 ]; then
        error "This script must be run with sudo"
    fi
}

main() {
    require_root

    log "Checking for packaging bug..."
    
    if [ ! -d "${LIB_DIR}" ]; then
        error "lm360 not installed (${LIB_DIR} not found)"
    fi

    # Check if bug exists: nested lm360/lm360/ directory
    if [ -d "${LIB_DIR}/lm360" ]; then
        log "BUG DETECTED: Nested directory structure"
        log "Found: ${LIB_DIR}/lm360/"
        log "Expected: ${LIB_DIR}/__init__.py"
        
        # Stop service to prevent crash-loop during repair
        if systemctl is-active --quiet "${SERVICE_NAME}"; then
            log "Stopping ${SERVICE_NAME}..."
            systemctl stop "${SERVICE_NAME}"
        fi
        
        log "Repairing package structure..."
        
        # Move contents up one level
        mv "${LIB_DIR}/lm360/"* "${LIB_DIR}/"
        rmdir "${LIB_DIR}/lm360"
        
        log "Verifying repair..."
        if [ -f "${LIB_DIR}/__init__.py" ] && [ -f "${LIB_DIR}/cli.py" ]; then
            log "✓ Package structure corrected"
        else
            error "Repair verification failed"
        fi
        
        # Restart service
        log "Starting ${SERVICE_NAME}..."
        systemctl start "${SERVICE_NAME}"
        sleep 2
        
        log "Checking service status..."
        if systemctl is-active --quiet "${SERVICE_NAME}"; then
            log "✓ Service running"
            systemctl status "${SERVICE_NAME}" --no-pager -l | head -15
        else
            log "WARNING: Service failed to start"
            journalctl -u "${SERVICE_NAME}" -n 20 --no-pager
            exit 1
        fi
        
        log ""
        log "Repair complete! Testing CLI..."
        if su -c "lm360 status" - "${SUDO_USER:-root}" 2>&1 | grep -q "Service"; then
            log "✓ CLI working"
        else
            log "Testing CLI with direct invocation..."
            /usr/local/bin/lm360 status || log "Note: Service may need to be running"
        fi
        
        log ""
        log "═══════════════════════════════════════"
        log "Repair successful!"
        log "Service: systemctl status ${SERVICE_NAME}"
        log "CLI test: lm360 status"
        log "═══════════════════════════════════════"
    else
        log "No bug detected - package structure is correct"
        log "Directory contents:"
        ls -la "${LIB_DIR}/" | head -10
        
        # Check if modules are importable
        log ""
        log "Testing Python import..."
        if python3 -c "import sys; sys.path.insert(0, '/usr/local/lib'); from lm360.cli import main; print('✓ Import successful')" 2>&1; then
            log "Package is correctly installed"
        else
            log "Import test failed - different issue may exist"
        fi
    fi
}

main "$@"
