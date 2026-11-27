# SeedSigner OS: cross-repo context

The SeedSigner application in this repo does not ship on its own. In production it runs on
**SeedSigner OS**, a purpose-built Linux system maintained in a separate repository:
[github.com/SeedSigner/seedsigner-os](https://github.com/SeedSigner/seedsigner-os).

The application is written against that system, not a general-purpose Linux host. This
document describes what the device actually is, so that assumptions about networking,
persistence, filesystems, and privileges start from the real environment. Where it
disagrees with the OS repo, the OS repo is right.

**If your task touches boot behavior, kernel configuration, packaging, image building, or
the runtime environment, clone the OS repo alongside this one and read it before proposing
changes:**

```bash
git clone --recursive https://github.com/SeedSigner/seedsigner-os.git
```

---

## 1. What seedsigner-os is

A set of [Buildroot](https://www.buildroot.org) external trees, one per board, that
cross-compile the kernel and userspace for Raspberry Pi hardware. A few parts are prebuilt binaries rather than built
from source: the Pi's GPU firmware and embit's bundled `libsecp256k1`.

Buildroot is a git submodule at `opt/buildroot`, pointing at SeedSigner's fork: upstream
Buildroot 2024.11.4 plus one commit to `package/python3/python3.mk` for reproducible
`.pyc` generation.

Docker is the supported build path (`Dockerfile`, `docker-compose.yml`); there is a
non-Docker path for Debian-based systems in `docs/without_docker.md`.

## 2. Layout

```
opt/build.sh                      the only build entrypoint
opt/buildroot/                    Buildroot submodule
opt/{pi0,pi02w,pi2,pi4}/          release board configs (each its own BR2_EXTERNAL tree)
opt/{pi0,pi02w,pi2,pi4}-dev/      developer board configs, layered on the release ones
opt/rootfs-overlay/               release userspace overlay
opt/rootfs-overlay-dev/           dev overlay, applied second
opt/external-packages/            Buildroot packages for the app's dependencies
opt/patches/                      patches to upstream sources (BR2_GLOBAL_PATCH_DIR)
```

A release board directory holds `configs/<board>_defconfig` and a `board/` with
`kernel.config`, `busybox.config`, `boot_config.txt`, `boot_cmdline.txt`, `post-build.sh`,
and `post-image-seedsigner.sh`.

The release overlay is small: `start.sh`, `etc/fstab`, `etc/shadow`, `etc/mdev.conf`,
`etc/mdev/mdev.sh`, and the `S02seedsigner` and `S10mdev` init scripts. It has no
`/etc/inittab` (Buildroot generates one), no network configuration, and no SSH.

## 3. Boot chain

1. On the Pi 0–3, the SoC's boot ROM loads `bootcode.bin` from the microSD card, which
   loads the GPU firmware `start_x.elf`. The Pi 4 boots from its EEPROM and loads
   `start4x.elf`.
2. That reads `config.txt` and `cmdline.txt`, then loads the kernel.
3. The CPU boots `zImage`, which contains the kernel **and** the whole root filesystem as
   an initramfs.
4. BusyBox init runs `/etc/init.d/S02seedsigner`, which runs `/start.sh`.
5. `/start.sh` does `cd /opt/src/` and then `/usr/bin/python3 main.py &`.

The app therefore runs as root, from `/opt/src`, in RAM.

## 4. How this repo's code gets into the image

**There is no Buildroot package for the application.** `opt/build.sh` clones this
repository (`dev` by default) with `--recurse-submodules` into the rootfs overlay's
`/opt`, so `src/main.py` becomes `/opt/src/main.py` on the device. `--app-repo`,
`--app-branch` and `--app-commit-id` choose what gets cloned, and `--skip-repo` uses app
code already placed in the overlay.

The build then processes the checkout (see the functions in `build.sh`):

- **`compile_translations_and_fonts()`** compiles the `.po` catalogs and trims the
  submodule's Arabic, CJK and Thai fonts down to the characters those catalogs use
  (skipped with `--skip-repo`).
- **`write_version_json()`** runs `tools/write_versionfile.py` to produce
  `src/seedsigner/version.json`. The app reads version information only from this file on
  SeedSigner OS, and raises at startup if it's missing or its `name` or `timestamp` is
  null, which looks like a boot hang. This repo's `.github/workflows/build.yml` checks the
  file for that reason.
- **`delete_unnecessary_files()`** deletes a fixed list of paths: today that is everything
  at the repo root apart from `src/`, plus the translation submodule's `.po` files, tools
  and git files. A new top-level file ships to the device unless it is added to that list.

The board's `post-build.sh` then byte-compiles `/opt/src` deterministically.

## 5. Security-relevant facts

The `kernel.config` files are build inputs, not the final configuration: Kconfig defaults
and Buildroot's own fixups (`LINUX_KCONFIG_FIXUP_CMDS` in `linux/linux.mk`) change some
values.

- **No TCP/IP networking, on any board.** `CONFIG_NET` is on, because Buildroot enables it
  for mdev's netlink hotplug events, but `INET`, `UNIX`, `PACKET`, `NETDEVICES`, Wi-Fi and
  Bluetooth are all off: there is no IP stack and no network interface. BusyBox is built
  without its networking applets, and `post-build.sh` removes Buildroot's network init
  script. On `pi02w` and `pi4` the radios are also disabled in `boot_config.txt`.
- **No loadable modules.** `CONFIG_MODULES` is off on every board, so no `.ko` files ship.
  Kconfig builds every `=m` line whose dependencies are met straight into the kernel
  instead, so those lines still have an effect.
- **No login.** Every account, root included, is locked. A getty does run on
  `/dev/console`, but nothing can log in to it. Release boards pass no `console=`
  argument on the kernel command line.
- **FAT only.** The release kernel supports FAT (`MSDOS_FS`, `VFAT_FS`) and cannot mount
  ext4.
- **What runs at boot:** `S01seedrng`, `S02seedsigner` (the app), `S10mdev` and
  `S50crond`. `post-build.sh` removes Buildroot's other init scripts, the rpi-userland demo
  binaries, and parts of the Python standard library (`asyncio`, `email`, `http`, `xml`,
  `tarfile`, `unittest`, `multiprocessing` and more). Code that imports a removed module passes CI
  and fails on the device; check `post-build.sh` for the full list.

## 6. The one persistent write path

The root filesystem is RAM-only and discarded on every power cycle.
`opt/rootfs-overlay/etc/fstab` mounts only `proc`, `devpts` and `sysfs`; its `/dev/root`
line is `noauto` and is never mounted.

The exception is the FAT boot partition. `etc/mdev.conf` routes `mmcblk0p1` hotplug events
to `etc/mdev/mdev.sh`, which does:

```sh
mount -o sync,nodirty $DEVNAME /mnt/microsd || mount -o sync $DEVNAME /mnt/microsd
echo -n "add" > /tmp/mdev_fifo
```

So `/mnt/microsd` is the card, mounted read-write with `sync`, and `/tmp/mdev_fifo` carries
the insert and remove events. `src/seedsigner/hardware/microsd.py` blocks reading that FIFO
(`MOUNT_POINT = "/mnt/microsd"`, `FIFO_PATH = "/tmp/mdev_fifo"`). `settings.json` is
written there only when the user enables persistent settings. Seeds are never written
there.

## 7. The hostname coupling

The single most important behavioral link between the two repos.
`src/seedsigner/models/settings.py`:

```python
HOSTNAME = platform.uname()[1]
SEEDSIGNER_OS = "seedsigner-os"
SETTINGS_FILENAME = "/mnt/microsd/settings.json" if HOSTNAME == SEEDSIGNER_OS else "settings.json"
```

The hostname is set by `BR2_TARGET_GENERIC_HOSTNAME` in the board defconfigs:
`"seedsigner-os"` on release images, `"seedsigner-dev"` on dev images. Three areas in this
repo branch on it:

- the settings file path and persistent settings (a relative `settings.json` elsewhere),
- microSD detection in `hardware/microsd.py`, which only watches the FIFO on SeedSigner OS
  (elsewhere `is_inserted` is always `True`),
- `helpers/version.py`, which reads only `version.json` on SeedSigner OS and blocks its
  git-based lookups with `@not_allowed_in_seedsigner_os`.

Changing the hostname string in only one of the two repos silently breaks all three.

## 8. Dev images versus release images

> *"They are not security-hardened: networking and SSH are enabled. Never use a dev image
> with real funds."* (seedsigner-os `docs/dev_images.md`)

Built with `./build.sh --<board> --dev`. A dev board config reuses the release kernel and
BusyBox configs with a fragment on top, and applies the dev overlay after the release one.

| | Release | Dev |
| --- | --- | --- |
| Networking | no IP stack, no interfaces | IP stack, Wi-Fi and Ethernet over DHCP, `wpa_supplicant`, `iw` |
| SSH | none | dropbear, root password `seedsigner`, or `authorized_keys` on the boot partition |
| Discovery | none | mDNS, reachable at `seedsigner.local` |
| USB gadget | none | `g_ether` on OTG boards (Zero, Zero W, Zero 2 W, Pi 4) |
| Console | no login, no `console=` argument | passwordless root shell on `tty1` |
| Partitions | 50 MiB image, one FAT16 partition | 256 MiB FAT plus a persistent ext4 data partition, grown on first boot |
| App source | baked-in `/opt/src` | prefers `/mnt/data/seedsigner/src/main.py` if present |
| Extras | none | pip, git, gh, rsync, bash, tmux, gdb, strace, and more |
| Slimming | full | skipped: complete Python stdlib and `.py` sources kept |

Dev-image behavior is not evidence about production behavior in either direction.

## 9. Boards and hardware

| Image | Boards | Flag |
| --- | --- | --- |
| `seedsigner_os.<tag>.pi0.img` | Pi Zero, Pi Zero W, Pi 1 Model B/B+ | `--pi0` |
| `seedsigner_os.<tag>.pi02w.img` | Pi Zero 2 W, Pi 3 Model B/B+ | `--pi02w` |
| `seedsigner_os.<tag>.pi2.img` | Pi 2 Model B | `--pi2` |
| `seedsigner_os.<tag>.pi4.img` | Pi 4 Model B | `--pi4` |

All boards build the same pinned `raspberrypi/linux` kernel (rpi-5.15.y) as 32-bit ARM,
with glibc and Python 3.12. They differ in CPU target, device trees, and firmware.

- **Display** is driven from Python over `spidev`. There is **no in-kernel panel driver**:
  the ST7789/ILI9341 drivers in `src/seedsigner/hardware/displays/` do the work.
- **Camera** uses the legacy MMAL stack (`start_x=1` in `boot_config.txt`, plus
  `rpi-userland` and `python-picamera`).
- **Buttons** use `RPi.GPIO` (through `/dev/gpiomem`); all button logic lives in this repo.
- **QR** decoding uses `zbar` and SeedSigner's `pyzbar` fork.

## 10. Building and reproducibility

```bash
export DOCKER_DEFAULT_PLATFORM=linux/amd64   # recommended by docs/building.md for reproducibility
export BOARD_TYPE=pi0
export RELEASE_TAG=x.y.z
git checkout $RELEASE_TAG
git submodule init && git submodule update
SS_ARGS="--$BOARD_TYPE --app-branch=$RELEASE_TAG" docker compose up --force-recreate --build
```

`build.sh` documents its other flags. Output lands in `images/`. Expect 25 minutes to 2.5+
hours and 20–30 GB of disk.

`BR2_REPRODUCIBLE=y` is set on every board, and the image build is deliberately
deterministic (fixed timestamps, disk and volume IDs, `mkfs.vfat --invariant`, normalized
file modes and sorted file lists), so building the same release tags should reproduce the
published hash. The `nodirty` FAT kernel patch keeps a used card byte-identical to the
flashed image.

**On signing:** the OS build prints a `sha256sum` of the finished image and signs nothing.
Release images are published on *this* repo's releases page with a SHA256 manifest that is
PGP-signed; verification instructions are in this repo's `README.md`.
