# Attack surface by version

The attacker's view: the attacker controls the AI server and can send anything from inside, and anyone can send anything from outside. For each way in, which software processes the input. The goal is a list that shrinks version by version, down to three pieces of software (network, tracker, verifier). Measured numbers (open ports, package and service counts) live in `book/src/results.md`; this page lists what handles each input.

## v0: stock Raspberry Pi OS Lite (64-bit), measured 29 Oct 2026

Kernel 6.18.50+rpt-rpi-v8, Debian 13, VideoCore firmware of 14 Sep 2026, bootloader EEPROM of 17 May 2026. Snapshot taken with the endpoint stopped (`device/measure.sh`, `nmap -p-` from the laptop); while it runs it adds TCP 8700 and one outgoing TCP link to the server.

| Way in | Who can use it | Software that processes the input |
|---|---|---|
| Ethernet port (wired) | server side and, on v0, also the outside (one shared link) | `bcmgenet` driver; kernel IPv4/IPv6, TCP and UDP; netfilter (modules loaded; rules not checked, needs `sudo nft list ruleset`) |
| TCP 22 | anyone on the link | OpenSSH server |
| UDP 5353 (IPv4 and IPv6) | anyone on the link | `avahi-daemon` (mDNS) |
| Two more UDP sockets (33762, 48578 at the time) | anyone on the link | not attributed: needs `sudo ss -tulpn` |
| TCP 8700, when the endpoint runs | users, and the server through its own connection | the endpoint (`pge-endpoint`); its proof checker runs as a child process |
| Wi-Fi radio | anyone in radio range | `brcmfmac` driver and the Wi-Fi chip's closed firmware, `wpa_supplicant`, NetworkManager |
| Bluetooth radio | anyone in radio range | `hci_uart`, `btbcm`, the kernel Bluetooth stack (`bluetooth`, `rfcomm`, `bnep`), `bluetoothd` |
| USB ports | anyone with physical access | kernel USB stack and any driver a device asks for |
| HDMI | anyone with physical access | `vc4` / `cec` drivers (CEC is an input channel) |
| SD card and boot | anyone with physical access | VideoCore boot firmware (closed), bootloader EEPROM, kernel; no secure boot |
| Serial console, keyboard | anyone with physical access | `getty` on tty1 |

Other running services that don't take network input directly: cron, dbus, journald, logind, timesyncd (makes outgoing NTP requests when it has a route), udevd, the user session.

**Gaps in this snapshot.** No UDP port scan from outside (needs root on the laptop). 691 TCP ports showed as filtered rather than closed; not explained yet (firewall rules weren't checked; rate limiting or the laptop's Internet Sharing bridge are other guesses). Physical inputs are out of scope (threat model) but listed so the list is complete.

## v1: stripped Buildroot image, booted 30 Oct 2026

Buildroot 2025.02.18, `image/build.sh` (`242cb4e`), endpoint binary sha256 `3ebfb66c...7a1a`. From outside: TCP 8700 only (connect scan of all ports; every other port refused). No SSH, so nothing was measured from inside; the list below is from the image contents.

| Way in | Who can use it | Software that processes the input |
|---|---|---|
| Ethernet port | server side and outside (one link) | `bcmgenet` (built into the kernel); kernel IPv4, TCP and UDP; IPv6 is a module that nothing loads (not verified on the running device); no firewall rules |
| TCP 8700 | users, and the server through its own outgoing connection | `pge-endpoint` as user `pge`; its checker as a child process with resource limits |
| Wi-Fi, Bluetooth | anyone in radio range | drivers are modules that nothing loads and the image ships no Wi-Fi firmware; not verified on the running device |
| Serial console, HDMI keyboard | physical access | `getty`; root logs in with an empty password (to fix) |
| SD card and boot | physical access | VideoCore boot firmware (closed), kernel; no secure boot; root file system mounted read-only |
| Data partition (from 30 Oct image `e498213`) | physical access, or root on the device | the signed update store, checked from scratch at every start (`docs/UPDATE_SPEC.md`); mounted `noexec`; a whole older copy of it is accepted (K43) |

Other services: `syslogd`, `klogd`, `crond` (removed from `abb7d3b`), `seedrng` (can't save its seed on the read-only root).

**Next image (`abb7d3b`, built 30 Oct, not booted yet):** netfilter built into the kernel and an `nftables` rule set loaded before the network: in, only new TCP connections to 8700 from 192.168.2.0/24; out, only new TCP connections to the server (192.168.2.1:8701); everything else dropped, ping included. The endpoint refuses to start if the rules aren't loaded. The rule set loaded cleanly in a Linux network namespace, and on the Pi (30 Oct, after a power cycle; image sha256 `a120f52c...4170`): ping and all 65,534 TCP ports other than 8700 are dropped, and the endpoint starts and answers.

**Scan artefacts.** Homebrew `nmap` on the laptop is blocked by macOS's Local Network permission (every port "host-unreach"); scans used Apple's Python instead. Parallel scans also time out on contiguous port ranges; those ports re-probed one at a time were closed. The 691 "filtered" ports on v0 (29 Oct) are most likely the same artefact.

**Rebuilt 2 Nov (`201ab5e`, not booted yet):** no login prompt and root locked; IPv6, Wi-Fi, Bluetooth, sound and USB not in the kernel; no modules on the image and module loading switched off at boot (the endpoint refuses to start otherwise); lockdown, Yama and Landlock on; `/dev/mem`, debugfs, KGDB, ftrace, kprobes, BPF and user namespaces off; the checker child under a system-call filter. The serial, Wi-Fi, Bluetooth and IPv6 rows above change once this image is checked on the Pi.

## Build machines (the supply chain)

Not a way into the running device, but whoever controls a build machine controls what the device runs. Nothing is virtualised on the device; the virtual machine below exists only on the laptop.

| Machine | What it produces | Checks today |
|---|---|---|
| GitHub Actions runner (`rust-endpoint.yml`) | the static aarch64 endpoint binary | upstream sources pinned by commit (`endpoint/sources.toml`), `--locked`; the binary baked into the image is the CI artifact, and `image/build.sh` prints its sha256 for comparison |
| Laptop VM (Lima, Ubuntu) running `image/build.sh` | the SD-card image: kernel, Buildroot user space, our overlay | Buildroot tarball sha256 pinned from its signed release; Buildroot's Pi config sets `BR2_DOWNLOAD_FORCE_CHECK_HASHES`, so every downloaded source (the Pi kernel included) must match a hash shipped in that tarball; after the build, checks that every config line survived and that no login, module or getty is left |
| Laptop (signing keys) | signed updates (`image/make_update.sh`) | the spec keeps the root key offline (`docs/UPDATE_SPEC.md`); the demo keys used so far are plain files on the laptop |

**Gaps.** A second build on a clean GitHub runner (`.github/workflows/image.yml`) matched the laptop's build file by file except for build metadata (2 Nov; the book's Measurements page, attack surface). That checked the user space, but not the kernel, which embedded the build host, time and a generated signing certificate. The v1.1 build removes those (reproducible mode, one build directory, no signing key): the laptop's VM and two clean GitHub runners produce the same files, kernel included, apart from those that depend on the signing key, so one compromised build machine can no longer change the image unnoticed if the builds are compared. What both still trust: Buildroot itself, the upstream sources and the hashes Buildroot ships for them. The host compilers and the VM image are not pinned, and nothing on the device checks what it boots (no secure boot).

## The end state (design)

Three pieces, from the 21 Oct mentor call: the network piece (only it touches the wire; possibly a simpler protocol than TCP/IP), the tracker (one answer per question, release time, failure cap) and the verifier (proof check in a locked-down process). Today all three are inside one Linux process plus the checker child, on a full kernel.
