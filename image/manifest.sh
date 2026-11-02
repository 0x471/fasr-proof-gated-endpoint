#!/usr/bin/env bash
# Lists every file in an SD-card image, one line each: partition, type, mode, owner, sha256 (or link
# target), path. Two builds can then be compared with diff; file times and file-system IDs are left out.
# Usage (Linux, as root: it mounts each partition read-only): image/manifest.sh sdcard.img > files.txt
set -euo pipefail
IMG=$1
[ "$(id -u)" = 0 ] || { echo "run as root (it mounts the partitions)" >&2; exit 2; }
LOOP="$(losetup --find --show --read-only --partscan "$IMG")"
MNT="$(mktemp -d)"
cleanup() { umount "$MNT" 2>/dev/null || true; rmdir "$MNT"; losetup -d "$LOOP"; }
trap cleanup EXIT
udevadm settle 2>/dev/null || true
parts=("$LOOP"p*)
[ "${#parts[@]}" = 3 ] || { echo "expected 3 partitions, found ${#parts[@]}" >&2; exit 1; }
for part in "${parts[@]}"; do
  n="p${part##*p}"
  case "$(blkid -o value -s TYPE "$part")" in
    ext4) opts=ro,noload ;;
    vfat) opts=ro ;;
    *) echo "$n: unexpected file system" >&2; exit 1 ;;
  esac
  mount -o "$opts" "$part" "$MNT"
  (cd "$MNT" && find . -mindepth 1 -printf '%p\t%y\t%m\t%U:%G\n' | LC_ALL=C sort | while IFS=$'\t' read -r path type mode owner; do
    case "$type" in
      f) what="$(sha256sum "$path" | cut -d' ' -f1)" ;;
      l) what="-> $(readlink "$path")" ;;
      *) what=- ;;
    esac
    printf '%s %s %s %s %s %s\n' "$n" "$type" "$mode" "$owner" "$what" "${path#./}"
  done)
  umount "$MNT"
done
