# SeedSigner OS: cross-repo context

The SeedSigner application in this repo does not ship on its own. In production it runs on
**SeedSigner OS**, a purpose-built Linux system maintained in a separate repository:
[github.com/SeedSigner/seedsigner-os](https://github.com/SeedSigner/seedsigner-os).

The application is written against that system, not a general-purpose Linux host. This
document describes what the device actually is, so that assumptions about networking,
persistence, filesystems, and privileges start from the real environment.

**If your task touches boot behavior, kernel configuration, packaging, image building, or
the runtime environment, clone the OS repo alongside this one and read it before proposing
changes:**

```bash
git clone --recursive https://github.com/SeedSigner/seedsigner-os.git
```

---

## 1. What seedsigner-os is

A [Buildroot](https://www.buildroot.org) external tree that cross-compiles a complete
Linux system — kernel and userspace — from source for Raspberry Pi hardware.

Buildroot itself is a git submodule at `opt/buildroot`, pinned to commit `bf2a2858aa` of
`github.com/seedsigner/buildroot`. That fork is **upstream Buildroot 2024.11.4 plus
exactly one commit**, which touches only `package/python3/python3.mk`: it adds
`-f --invalidation-mode=checked-hash` to `.pyc` generation and disables Buildroot's
`PYTHON3_REMOVE_PY_FILES` finalize hook so the boards' own `post-build.sh` can handle it
instead. Both changes serve reproducible builds; the fork carries no other delta from
upstream.

Docker is the supported build path (`Dockerfile`, `docker-compose.yml`); there is a
Debian-only non-Docker path in `docs/without_docker.md`.

## 2. Layout

```
opt/build.sh                      the only build entrypoint
opt/buildroot/                    submodule, pinned commit
opt/{pi0,pi02w,pi2,pi4}/          release board configs
opt/{pi0,pi02w,pi2,pi4}-dev/      developer board configs
opt/rootfs-overlay/               release userspace overlay
opt/rootfs-overlay-dev/           dev overlay, applied second
opt/external-packages/            custom Buildroot packages
opt/patches/                      BR2_GLOBAL_PATCH_DIR
```

Each release board directory contains `configs/<board>_defconfig` and a `board/` holding
`kernel.config`, `busybox.config`, `boot_config.txt`, `boot_cmdline.txt`, `post-build.sh`,
and `post-image-seedsigner.sh`.

**The entire release userspace overlay is eight files** — this is the whole delta on top of
the Buildroot skeleton:

```
opt/rootfs-overlay/start.sh
opt/rootfs-overlay/etc/fstab
opt/rootfs-overlay/etc/shadow
opt/rootfs-overlay/etc/mdev.conf
opt/rootfs-overlay/etc/mdev/mdev.sh
opt/rootfs-overlay/etc/init.d/S02seedsigner
opt/rootfs-overlay/etc/init.d/S10mdev
opt/rootfs-overlay/.gitignore
```

There is no `/etc/inittab`, no network configuration, and no SSH in the release overlay.

`opt/external-packages/` holds Buildroot packages for this project's Python dependencies:
`python-embit`, `python-pyzbar` (SeedSigner's pyzbar fork), `python-urtypes`,
`python-picamera`, `python-pillow-ep`, `python-mock`, `libraqm`, plus `gh` (dev images
only). Each carries a `.hash` file with checksums for its source tarball.

`opt/patches/` contains two patches applied to upstream sources: a FAT `nodirty` mount
option for the kernel (so a flashed card can be byte-compared against the published image
without the driver setting the volume dirty flag), and a numpy patch that blanks
build-machine info for cross-architecture reproducibility.

## 3. Boot chain

1. The Pi's GPU bootloader reads the microSD card and loads `bootcode.bin`.
2. `start_x.elf` reads `config.txt` and `cmdline.txt`, then loads the kernel.
3. The CPU boots `zImage` — which contains the kernel **and** the entire root filesystem.
4. BusyBox init runs `/etc/init.d/S02seedsigner`, which runs `/start.sh`.
5. `/start.sh` is three lines: `cd /opt/src/` then `/usr/bin/python3 main.py &`.

The app therefore runs as root, from `/opt/src`, in RAM.

## 4. How this repo's code gets into the image

**There is no Buildroot package for the application.** `opt/build.sh` clones this
repository directly into the rootfs overlay:

```sh
seedsigner_app_repo="https://github.com/SeedSigner/seedsigner.git"
seedsigner_app_repo_branch="dev"
git clone --recurse-submodules --depth 1 -b "${branch}" "${repo}" "${rootfs_overlay}/opt/"
```

`--app-repo`, `--app-branch`, and `--app-commit-id` override the defaults;
`--app-commit-id` does a full clone plus `git reset --hard`. Because
`BR2_ROOTFS_OVERLAY="../rootfs-overlay/"`, the checkout lands at `/opt` on the device, so
`src/main.py` becomes `/opt/src/main.py`.

The build then processes the checkout:

- **`compile_translations_and_fonts()`** creates a virtualenv, installs Babel and
  fonttools, runs `python3 setup.py compile_catalog`, then uses `pyftsubset` to subset the
  bundled fonts down to only the glyphs the compiled translations actually use, deleting
  the originals. Font size is a real constraint on a 50 MB image.
- **`write_version_json()`** runs `tools/write_versionfile.py` with
  `SEEDSIGNER_OS_BUILDER=1` to produce `src/seedsigner/version.json`. This file is
  load-bearing: a missing file or a null field makes the app raise at the splash screen,
  which presents as an unrecoverable boot hang. This repo's `.github/workflows/build.yml`
  asserts on it explicitly for that reason.
- **`delete_unnecessary_files()`** strips `.github`, `docker`, `docs`, `enclosures`,
  `l10n`, `seedsigner-screenshots`, `tests`, `tools`, all `.git*`, `requirements*.txt`,
  `setup.*`, `pyproject.toml`, `seedsigner_pubkey.gpg`, and every `.po` file.

**A release device therefore has no tests, no tools, no `.git`, and no packaging
metadata.** The board's `post-build.sh` then byte-compiles `/opt/src` deterministically
(`SOURCE_DATE_EPOCH=1 PYTHONHASHSEED=0 --invalidation-mode=checked-hash`).

## 5. Security posture

Effective kernel values, after Kconfig defaults and `select` statements are resolved. Note
that the `kernel.config` files in the OS repo are build inputs, so a symbol's value there is
not always its final one.

| | pi0 | pi02w | pi2 | pi4 |
| --- | --- | --- | --- | --- |
| `CONFIG_NET` | `n` | `n` | `n` | `n` |
| `CONFIG_MODULES` | `n` | `n` | `n` | `n` |
| `CONFIG_USB` | `n` | `y` | `y` | `y` |
| `CONFIG_SERIAL_8250_CONSOLE` / `AMBA_PL011_CONSOLE` | `n` | `y` | `y` | `y` |
| `CONFIG_EXT4_FS` | `n` | `n` | `n` | `n` |
| `CONFIG_SUSPEND` | `n` | `n` | `n` | `n` |
| `CONFIG_I2C` | `y` | `y` | `y` | `y` |
| `CONFIG_SWAP` | `y` | `y` | `y` | `y` |
| `dtoverlay=disable-wifi` / `-bt` | no | yes | yes | yes |

**No networking, on any board.** `CONFIG_NET` is `n` on all four boards, so there is no
socket layer at all: no
`NETDEVICES`, no `CFG80211`/`MAC80211`, no `BRCMFMAC`, no Bluetooth. No wifi firmware
package is enabled in the release defconfigs. BusyBox is built without `ifconfig`,
`iproute`, `ping`, `route`, `netcat`, `nslookup`, `httpd`, `arp`, `wget`, or `udhcpc`, and
`post-build.sh` deletes Buildroot's `S40network` init script. On `pi02w`/`pi2`/`pi4` the
radios are *additionally* disabled at the device-tree level in `boot_config.txt` — defense
in depth on top of a kernel that cannot use them.

**Nothing loadable at runtime.** `CONFIG_MODULES=n` on all four boards, so every `=m` line
in those config files is dead and no `.ko` files ship.

**Root is locked.** `opt/rootfs-overlay/etc/shadow` ships `root:*:::::::` (and `*` for
every other account). Note the release defconfigs contain
`BR2_TARGET_GENERIC_ROOT_PASSWD="passworDT"` — this is **inert**. Buildroot's password hook
runs before overlays are copied onto the target tree, so the overlay's locked shadow file
always overwrites it. The dev board configs have to explicitly re-apply a password in their
`post-build.sh` to undo this, and say so in comments.

**A getty does run, and cannot be logged into.** The release overlay ships no
`/etc/inittab`, so Buildroot installs its own (`package/busybox/inittab`) and rewrites it
at build time. `BR2_TARGET_GENERIC_GETTY` defaults to `y` and `BR2_TARGET_GENERIC_GETTY_PORT`
defaults to `"console"`; no release defconfig overrides either, so `busybox.mk` substitutes
the template's commented-out getty line for a live one:

```
console::respawn:/sbin/getty -L  console  vt100
```

So a login prompt *is* respawned on `/dev/console`. It cannot be satisfied: the only
account is `root`, and `root` has no valid password hash. No login is possible; a getty
does nonetheless exist. Which physical interface `/dev/console` reaches is determined by
the board's device tree at boot.

**USB and serial, precisely.** `CONFIG_USB` and the 8250/PL011 console drivers *are* built
on `pi02w`, `pi2`, and `pi4` (not on `pi0`). However, **no release board passes a
`console=` argument**: `boot_cmdline.txt` is empty on `pi02w`/`pi2`/`pi4` and contains only
`spidev.bufsiz=131072` on `pi0`. `CONFIG_I2C` is `y` on all four boards, though
its bus drivers are `=m` and therefore dead under `CONFIG_MODULES=n`.

**Filesystem.** Only `CONFIG_MSDOS_FS` and `CONFIG_VFAT_FS` — the release kernel cannot
mount ext4 at all. `CONFIG_SUSPEND` is `n`.

**Swap is compiled in but never used.** `CONFIG_SWAP` is `y` on all four boards — the board
configs comment out `CONFIG_ZSWAP`/`CONFIG_FRONTSWAP`/`CONFIG_NFS_SWAP` but never disable
`CONFIG_SWAP` itself, which defaults on — and BusyBox's inittab runs `swapon -a` at sysinit.
Nothing is ever swapped: `/etc/fstab` declares no swap entry and the image contains no swap
partition or file.

**Slimming.** `post-build.sh` deletes the `syslogd`, `klogd`, `sysctl`, `mdev`, `seedrng`,
`network`, and `pigpio` init scripts; the rpi-userland demo binaries (`raspistill`,
`raspivid`, `vcgencmd`, `dtoverlay`, `zbarcam`, …); and Python stdlib subsystems with no
importer — `asyncio`, `email`, `xml`, `http`, `multiprocessing`, `wsgiref`, `venv`,
`zoneinfo`, `unittest`, `ensurepip`, plus the matching C extensions. Only `.pyc` files ship
for the stdlib.

## 6. The one persistent write path

The root filesystem is RAM-only and discarded on every power cycle. `opt/rootfs-overlay/etc/fstab`
mounts only `proc`, `devpts`, and `sysfs`; its `/dev/root` line is `rw,noauto` and is never
actually mounted.

The exception is the FAT boot partition. `etc/mdev.conf` routes `mmcblk0p1` hotplug events
to `etc/mdev/mdev.sh`, which does:

```sh
mount -o sync,nodirty $DEVNAME /mnt/microsd || mount -o sync $DEVNAME /mnt/microsd
echo -n "add" > /tmp/mdev_fifo
```

So `/mnt/microsd` is the card, mounted read-write with `sync`, and `/tmp/mdev_fifo` is the
insert/remove signal. This is what `src/seedsigner/hardware/microsd.py` reads
(`MOUNT_POINT = "/mnt/microsd"`, `FIFO_PATH = "/tmp/mdev_fifo"`) and where
`Settings.SETTINGS_FILENAME` points when persistent settings are enabled. Seeds are never
written there.

## 7. The hostname coupling

The single most important behavioral link between the two repos. `src/seedsigner/models/settings.py`:

```python
HOSTNAME = platform.uname()[1]
SEEDSIGNER_OS = "seedsigner-os"
SETTINGS_FILENAME = "/mnt/microsd/settings.json" if HOSTNAME == SEEDSIGNER_OS else "settings.json"
```

The hostname is set by `BR2_TARGET_GENERIC_HOSTNAME` in the board defconfigs:
`"seedsigner-os"` on release images, `"seedsigner-dev"` on dev images. Three subsystems in
this repo branch on it:

- the settings file path falls back to a relative `settings.json` off SeedSigner OS,
- the microSD insert/remove polling thread in `hardware/microsd.py` only runs on
  SeedSigner OS (elsewhere `is_inserted` is hardcoded `True`),
- `helpers/version.py` gates its git-based lookups behind a `NotAllowedInSeedSignerOS`
  guard.

If you change any of these, changing the hostname string in either repo alone will silently
break the coupling.

## 8. Dev images versus release images

> *"They are not security-hardened: networking and SSH are enabled. Never use a dev image
> with real funds."* — seedsigner-os `docs/dev_images.md`

Built with `./build.sh --<board> --dev`. The dev board config deliberately *references* the
release kernel and busybox configs and layers a fragment on top, and sets
`BR2_ROOTFS_OVERLAY="../rootfs-overlay/ ../rootfs-overlay-dev/"` so the dev overlay is
applied second and wins.

| | Release | Dev |
| --- | --- | --- |
| Networking | absent from kernel and userspace | `CONFIG_NET`/`INET`/`CFG80211`/`BRCMFMAC` on; wifi firmware, `wpa_supplicant`, `iw` |
| SSH | none | dropbear, root password `seedsigner`, or `authorized_keys` on the boot partition |
| Discovery | none | mDNS, reachable at `seedsigner.local` |
| USB gadget | none | `dtoverlay=dwc2` + `g_ether`, static `10.55.0.1`, `udhcpd` |
| Console | no `console=` argument, root locked | passwordless root shell on `tty1` and serial |
| Partitions | one 50 MB FAT32 | 256 MB FAT (`SEEDSIGNDEV`) + persistent ext4 (`seedsigner-data`), grown on first boot |
| App source | baked-in `/opt/src` | prefers `/mnt/data/seedsigner/src/main.py` if present |
| Extras | none | pip, git, gh, rsync, bash, tmux, gdb, strace, htop, jq, gnupg2, nano, parted |
| Slimming | full | skipped — complete Python stdlib and `.py` sources kept |

Dev-image behavior is not evidence about production behavior in either direction.

## 9. Boards and hardware

| Image | Boards | Flag |
| --- | --- | --- |
| `seedsigner_os.<tag>.pi0.img` | Pi Zero, Pi Zero W | `--pi0` |
| `seedsigner_os.<tag>.pi02w.img` | Pi Zero 2 W, Pi 3 Model B | `--pi02w` |
| `seedsigner_os.<tag>.pi2.img` | Pi 2 Model B | `--pi2` |
| `seedsigner_os.<tag>.pi4.img` | Pi 4 Model B | `--pi4` |

All boards build the same pinned `raspberrypi/linux` kernel tarball (commit
`14b35093ca68`, rpi-5.15.y) as 32-bit ARM against a glibc toolchain with Python 3.12. They
differ in CPU target (`arm1176jzf_s` / `cortex_a53` / `cortex_a7` / `cortex_a72`), device
tree names, and firmware variant (`PI_X` versus `PI4_X` for the Pi 4).

- **Display** is driven from Python over `spidev` (`dtparam=spi=on`, `CONFIG_SPI_SPIDEV`,
  `CONFIG_SPI_BCM2835`). There is **no in-kernel panel driver** — the ST7789/ILI9341
  drivers in `src/seedsigner/hardware/displays/` do the work.
- **Camera** uses the legacy MMAL stack: `start_x=1` in `boot_config.txt`, plus
  `rpi-userland` and `python-picamera`.
- **Buttons** use `RPi.GPIO` over `CONFIG_GPIO_SYSFS`; all button logic lives in this repo.
- **QR** decoding uses `zbar` and SeedSigner's `pyzbar` fork.

## 10. Building and reproducibility

```bash
export DOCKER_DEFAULT_PLATFORM=linux/amd64   # required for a reproducible result
export BOARD_TYPE=pi0
export RELEASE_TAG=x.y.z
git checkout $RELEASE_TAG
git submodule init && git submodule update
SS_ARGS="--$BOARD_TYPE --app-branch=$RELEASE_TAG" docker compose up --force-recreate --build
```

Other `build.sh` flags: `--all`, `--dev`, `--no-clean`, `--skip-repo`, `--app-repo`,
`--app-commit-id`, `--no-op`. Output lands in `images/seedsigner_os.<branch>.<board>.img`.
Expect 25 minutes to 2.5+ hours and 20–30 GB of disk.

`BR2_REPRODUCIBLE=y` is set on every board, and the image build is deliberately
deterministic: a fixed disk timestamp, a fixed FAT volume ID and label, `mkfs.vfat
--invariant`, `chmod`/`touch` normalization of every boot file, sorted globbing instead of
directory copies, and the `nodirty` FAT kernel patch so a card can be byte-compared to the
flashed image. A build that reproduces should match the published release hash.

**On signing:** the OS build prints a `sha256sum` of the finished image and does no signing
of any kind. Release images are published and PGP-signed on *this* repo's releases page;
verification instructions are in this repo's `README.md`.
