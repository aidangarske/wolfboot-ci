# wolfBoot CI Container Images

Pre-built Docker images for wolfBoot GitHub Actions CI, eliminating per-run
toolchain downloads and apt-get overhead.

## Images

All images use Devuan testing as the base (except renode).

| Image | Purpose | Base |
|-------|---------|------|
| `wolfboot-ci-base` | Shared foundation: build-essential, cmake, ninja, python3, libwolfssl-dev | devuan:testing |
| `wolfboot-ci-arm` | ARM cross-compilation: arm-none-eabi-gcc, aarch64-linux-gnu, clang | base |
| `wolfboot-ci-powerpc` | PowerPC cross-compilation: powerpc-linux-gnu-gcc | base |
| `wolfboot-ci-sim` | Host simulator tests: 32-bit libc, libcheck | base |
| `wolfboot-ci-m33mu` | TrustZone emulator tests: ARM toolchain + m33mu + MCUXpresso SDK | devuan:testing |
| `wolfboot-ci-riscv` | RISC-V: xPack GCC + freedom-e-sdk | base |
| `wolfboot-ci-aarch64` | Bare-metal AArch64: aarch64-none-elf toolchain | base |
| `wolfboot-ci-x86` | x86 QEMU: nasm, gcc-multilib, qemu-system-x86, swtpm | base |
| `wolfboot-ci-renode` | Renode emulation: renode + arm-none-eabi-gcc | antmicro/renode |

## Building locally

```bash
# Build base first
podman build --no-cache -t wolfboot-ci-base:testing base/

# Build derived images (replace 'arm' with any image name)
podman build --no-cache --build-arg BASE_TAG=testing -t wolfboot-ci-arm:testing arm/

# Build m33mu image
podman build --no-cache -t wolfboot-ci-m33mu:testing m33mu/
```

## MCUXpresso SDK (m33mu image)

wolfBoot's NXP targets need a west-provisioned MCUXpresso SDK tree and NXP's
CMSIS_5 fork; without them a build stops at `fsl_common.h: No such file or
directory`. The m33mu image ships both, and exports

    MCUXPRESSO=/opt/nxp/mcuxpresso-sdk/mcuxsdk
    MCUXPRESSO_CMSIS=/opt/nxp/CMSIS_5/CMSIS

wolfBoot's example configs set these with `?=`, so the environment wins and
jobs need no extra make arguments — plain `make` works.

Boards are provisioned into one shared west workspace. `west update_board`
updates only its own board's projects, so boards accumulate:

```bash
# Add or change the board set (default: lpcxpresso55s69 frdmmcxn947 mimxrt700evk)
podman build --no-cache \
  --build-arg MCUX_BOARDS="lpcxpresso55s69 frdmmcxn947 frdmmcxa153" \
  -t wolfboot-ci-m33mu:testing m33mu/

# Keep the full SDK instead of pruning to the subtrees wolfBoot references
podman build --no-cache --build-arg MCUX_PRUNE=0 -t wolfboot-ci-m33mu:testing m33mu/
```

Boards share most repositories, so extra boards are far cheaper than the
first: `lpcxpresso55s69` alone costs ~3.0 GB, `+frdmmcxn947` ~2.5 GB more,
and `+mimxrt700evk` only ~145 MB. The default prune (dropping `middleware`,
`rtos`, `docs`, the non-`_boards` examples, and the `.git` directories, none
of which any wolfBoot makefile names) takes the three-board default from
~5.8 GB to ~2.8 GB.

## Usage in GitHub Actions

```yaml
jobs:
  build:
    runs-on: ubuntu-latest
    container:
      image: ghcr.io/wolfssl/wolfboot-ci-arm:latest
    steps:
      - uses: actions/checkout@v4
        with:
          submodules: true
      - name: Init submodules
        run: |
          git config --global --add safe.directory "$GITHUB_WORKSPACE"
          git submodule update --init --single-branch
      - name: Build
        run: make
```

## Publishing

Images are automatically built and published to GHCR when a version tag is pushed:

```bash
git tag v1.0
git push origin v1.0
```

Individual images can also be built via workflow dispatch.
