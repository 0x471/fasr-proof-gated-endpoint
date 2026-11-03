#!/usr/bin/env bash
# Runs after the board's post-image script: adds a dm-verity hash tree for the root file system, a
# kernel command line that checks every root block against it, and a writable partition holding the
# update store, so updates can be applied while the root file system stays read-only.
set -euo pipefail
: "${PGE_DATA:?build.sh sets PGE_DATA}"
rm -f "$BINARIES_DIR/data.ext4" "$BINARIES_DIR/verity.img" "$BINARIES_DIR/boot.vfat" "$BINARIES_DIR/sdcard.img"
# Root owns the store on the device; the endpoint (user pge) only reads it.
"$HOST_DIR/bin/fakeroot" -- sh -c 'chown -R 0:0 "$1" && chmod -R go-w "$1" && "$2/sbin/mkfs.ext4" -q -L data -U 70676500-0000-4000-8000-000000000003 -E hash_seed=70676500-0000-4000-8000-000000000004 -d "$1" "$3" 64M' \
  sh "$PGE_DATA" "$HOST_DIR" "$BINARIES_DIR/data.ext4"

# A fixed salt: a random one would differ in every build, so two builds couldn't be compared. The
# salt only stops one precomputed table from serving many hash trees.
SALT=7067652d726f6f742d76657269747920
size="$(stat -L -c %s "$BINARIES_DIR/rootfs.ext4")"
[ $((size % 4096)) -eq 0 ] || { echo "rootfs.ext4 is not a whole number of 4 KiB blocks" >&2; exit 1; }
hash="$("$HOST_DIR/sbin/veritysetup" format --no-superblock --hash sha256 --salt "$SALT" \
  --data-block-size 4096 --hash-block-size 4096 "$BINARIES_DIR/rootfs.ext4" "$BINARIES_DIR/verity.img" \
  | sed -n 's/^Root hash:[[:space:]]*//p')"
[ "${#hash}" -eq 64 ] || { echo "veritysetup gave no root hash" >&2; exit 1; }
# The kernel builds the checked device itself (CONFIG_DM_INIT) once both partitions exist, and mounts
# it read-only as the root. mitigations=auto: this kernel (6.6.28) defines the switch for x86 only, so
# on arm64 it starts with every speculative-execution mitigation off unless told otherwise.
# PGE_CMDLINE_EXTRA adds options for one experiment's image.
printf 'root=/dev/dm-0 dm-mod.waitfor=/dev/mmcblk0p2,/dev/mmcblk0p4 dm-mod.create="root,,,ro,0 %d verity 1 /dev/mmcblk0p2 /dev/mmcblk0p4 4096 4096 %d 0 sha256 %s %s" mitigations=auto rootwait console=tty1 console=ttyAMA0,115200%s\n' \
  $((size / 512)) $((size / 4096)) "$hash" "$SALT" "${PGE_CMDLINE_EXTRA:+ $PGE_CMDLINE_EXTRA}" \
  > "$BINARIES_DIR/rpi-firmware/cmdline.txt"

# The board script's boot partition, rebuilt with this command line and a fixed volume id (mkdosfs
# picks a random one), then all four partitions.
{ sed '/^image sdcard.img/,$d; s/^\([[:space:]]*\)vfat {$/&\n\1\textraargs = "-i 70676505"/' "$BINARIES_DIR/genimage.cfg"
  cat <<'CFG'
image sdcard.img {
	hdimage {
	}
	partition boot {
		partition-type = 0xC
		bootable = "true"
		image = "boot.vfat"
	}
	partition rootfs {
		partition-type = 0x83
		image = "rootfs.ext4"
	}
	partition data {
		partition-type = 0x83
		image = "data.ext4"
	}
	partition verity {
		partition-type = 0xDA
		image = "verity.img"
	}
}
CFG
} > "$BINARIES_DIR/genimage-data.cfg"
grep -q '^image boot.vfat' "$BINARIES_DIR/genimage-data.cfg" || { echo "no boot partition in the board's genimage.cfg" >&2; exit 1; }
root="$(mktemp -d)"
trap 'rm -rf "$root"' EXIT
rm -rf "$BUILD_DIR/genimage-data.tmp"
genimage --rootpath "$root" --tmppath "$BUILD_DIR/genimage-data.tmp" --inputpath "$BINARIES_DIR" \
  --outputpath "$BINARIES_DIR" --config "$BINARIES_DIR/genimage-data.cfg"
