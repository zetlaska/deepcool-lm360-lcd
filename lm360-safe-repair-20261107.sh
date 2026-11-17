#!/bin/bash
# Operational wrapper for the supplied package-directory repair; no driver changes.
set -euo pipefail
[[ $EUID -eq 0 ]] || { echo "Run this script with sudo."; exit 1; }
base=/usr/local/lib/lm360
repair=/home/silver/Documents/lm360/repair-package-20261107.sh
printf '%s  %s\n' 0a29bb8c7b728b6ad4f4b6f07f78995a98b3e76ce32d04d325633910d07c3ca2 "$repair" | sha256sum -c -
[[ -d "$base/lm360" ]] || { echo "Expected nested package not present; aborting without changes."; exit 1; }
[[ -f "$base/lm360/cli.py" && -f "$base/lm360/__init__.py" ]] || exit 1
shopt -s nullglob dotglob
for item in "$base/lm360/"*; do
    name=${item##*/}
    [[ "$name" != .* ]] || { echo "Unexpected hidden entry: $name; aborting."; exit 1; }
    [[ ! -e "$base/$name" && ! -L "$base/$name" ]] || { echo "Destination conflict: $name; aborting."; exit 1; }
done
if systemctl is-active --quiet deepcool-lm.service || systemctl is-active --quiet deepcool-lm-arkui.service; then
    echo "Legacy LCD service is active; aborting to prevent dual USB ownership."; exit 1
fi
backup=$(mktemp -d /var/backups/lm360-package-repair-XXXXXXXX)
cp -a "$base" "$backup/installed-package"
systemctl cat lm360.service > "$backup/lm360.service.txt"
systemctl show lm360.service deepcool-lm.service -p Id -p ActiveState -p UnitFileState > "$backup/service-states.txt"
echo "Backup: $backup"
systemctl stop lm360.service
# Original script can report a pipeline failure despite a completed repair.
set +e
bash "$repair"
result=$?
set -e
echo "Original repair script exit: $result"
[[ -f "$base/cli.py" && -f "$base/__init__.py" && ! -d "$base/lm360" ]] || { echo "Repair incomplete; backup preserved at $backup; service left stopped if applicable."; exit 1; }
systemctl is-active --quiet lm360.service || systemctl start lm360.service
systemctl status lm360.service --no-pager
/usr/local/bin/lm360 status
echo "Repair applied; verify sustained operation separately. Backup: $backup"
