# m33mu-ci: Devuan testing CI image for Zephyr + m33mu
FROM docker.io/devuan/devuan:testing

ENV DEBIAN_FRONTEND=noninteractive

ENV ARM_GCC_VERSION=15.2.rel1
ENV ARM_GCC_TARBALL=arm-gnu-toolchain-15.2.rel1-x86_64-arm-none-eabi.tar.xz
ENV ARM_GCC_DIR=arm-gnu-toolchain-15.2.rel1-x86_64-arm-none-eabi

# ---- Base build tooling + deps (as provided) ----
RUN apt-get update && apt-get install -y --no-install-recommends \
    ca-certificates curl wget xz-utils file \
    git build-essential pkg-config \
    autoconf automake libtool \
    cmake ninja-build \
    rustc cargo \
    python3 python3-pip python3-venv python3-full \
    gdb-multiarch \
    libtpms-dev vde2 \
    libcapstone-dev \
    libvdeplug-dev \
    vde-switch \
    libdw-dev libelf-dev \
    libncurses-dev \
    && rm -rf /var/lib/apt/lists/* \
    && apt-get clean

# ---- wolfSSL: build from source (removed from Debian/Devuan testing) ----
ENV WOLFSSL_VERSION=v5.9.2-stable

RUN set -eux; \
    wget -q "https://github.com/wolfSSL/wolfssl/archive/refs/tags/${WOLFSSL_VERSION}.tar.gz" -O /tmp/wolfssl.tar.gz; \
    tar -C /tmp -xf /tmp/wolfssl.tar.gz; \
    cd /tmp/wolfssl-*; \
    ./autogen.sh; \
    ./configure --enable-distro; \
    make -j"$(nproc)"; \
    make install; \
    install -m 0644 wolfssl/options.h /usr/local/include/wolfssl/options.h; \
    ldconfig; \
    rm -rf /tmp/wolfssl*

RUN set -eux; \
    cd /tmp; \
    wget -q "https://armkeil.blob.core.windows.net/developer/files/downloads/gnu/${ARM_GCC_VERSION}/binrel/${ARM_GCC_TARBALL}"; \
    mkdir -p /opt/toolchains; \
    tar -C /opt/toolchains -xf "${ARM_GCC_TARBALL}"; \
    ln -sf "/opt/toolchains/${ARM_GCC_DIR}/bin/arm-none-eabi-"* /usr/local/bin/; \
    rm -f "${ARM_GCC_TARBALL}"

ENV PATH="/opt/toolchains/${ARM_GCC_DIR}/bin:${PATH}"

RUN printf 'int main(void){return 0;}\n' > /tmp/arm-none-eabi-smoke.c \
    && arm-none-eabi-gcc --specs=nano.specs --specs=nosys.specs /tmp/arm-none-eabi-smoke.c -o /tmp/arm-none-eabi-smoke.elf \
    && rm -f /tmp/arm-none-eabi-smoke.c /tmp/arm-none-eabi-smoke.elf

# ---- Zephyr SDK ----
#ARG ZEPHYR_SDK_VERSION=0.17.4
#ARG ZEPHYR_SDK_ARCH=linux-x86_64
#
#RUN set -eux; \
#    cd /tmp; \
#    wget -q "https://github.com/zephyrproject-rtos/sdk-ng/releases/download/v${ZEPHYR_SDK_VERSION}/zephyr-sdk-${ZEPHYR_SDK_VERSION}_${ZEPHYR_SDK_ARCH}.tar.xz"; \
#    wget -q "https://github.com/zephyrproject-rtos/sdk-ng/releases/download/v${ZEPHYR_SDK_VERSION}/sha256.sum"; \
#    grep "zephyr-sdk-${ZEPHYR_SDK_VERSION}_${ZEPHYR_SDK_ARCH}.tar.xz" sha256.sum | sha256sum -c -; \
#    mkdir -p /opt; \
#    tar -C /opt -xf "zephyr-sdk-${ZEPHYR_SDK_VERSION}_${ZEPHYR_SDK_ARCH}.tar.xz"; \
#    rm -f "zephyr-sdk-${ZEPHYR_SDK_VERSION}_${ZEPHYR_SDK_ARCH}.tar.xz" sha256.sum
#
#ENV ZEPHYR_TOOLCHAIN_VARIANT=zephyr
#ENV ZEPHYR_SDK_INSTALL_DIR=/opt/zephyr-sdk-${ZEPHYR_SDK_VERSION}
#
## ---- Python venv for west (avoids PEP 668 externally-managed-environment) ----
#ENV VIRTUAL_ENV=/opt/venv
#ENV PATH="${VIRTUAL_ENV}/bin:${PATH}"
#
#RUN python3 -m venv "${VIRTUAL_ENV}" \
# && "${VIRTUAL_ENV}/bin/pip" install --no-cache-dir --upgrade pip setuptools wheel \
# && "${VIRTUAL_ENV}/bin/pip" install --no-cache-dir west


# ---- MCUXpresso SDK (west workspace) ----
# wolfBoot's NXP targets (lpc55s69, mcxn, mcxa, mcxw, imx-rt*) build against a
# west-provisioned MCUXpresso SDK tree plus NXP's CMSIS_5 fork. Without them a
# job in this image dies at `fsl_common.h: No such file or directory`.
#
# `west update_board` runs `west update -n -o=--depth=1 <projects>`, updating
# only that board's projects, so boards accumulate in one workspace: add a
# board by appending it to MCUX_BOARDS.
#
# The se_hostlib/emwin projects are dropped from each board manifest (they are
# not publicly fetchable), matching wolfBoot's
# .github/workflows/test-build-mcux-sdk-manifests.yml.
ARG MCUX_BOARDS="lpcxpresso55s69 frdmmcxn947 mimxrt700evk"

# Keep only the subtrees wolfBoot's build actually references: devices,
# drivers, components, CMSIS, arch and examples/_boards/<board>. middleware,
# rtos, docs and the non-_boards examples are never named by any wolfBoot
# makefile and dominate the tree, so they are pruned. Set MCUX_PRUNE=0 to keep
# the full SDK if a future target needs more of it.
ARG MCUX_PRUNE=1

ENV MCUX_ROOT=/opt/nxp
ENV MCUXPRESSO=/opt/nxp/mcuxpresso-sdk/mcuxsdk
ENV MCUXPRESSO_CMSIS=/opt/nxp/CMSIS_5/CMSIS

# west lives in its own venv (Devuan testing is PEP 668 externally-managed).
# Deliberately NOT on the global PATH: nothing at build time needs west, and
# leaving the image's default python3 untouched keeps this change invisible to
# every other job that uses the image.
RUN set -eux; \
    python3 -m venv /opt/venv; \
    /opt/venv/bin/pip install --no-cache-dir --upgrade pip setuptools wheel; \
    /opt/venv/bin/pip install --no-cache-dir west

RUN set -eux; \
    mkdir -p "${MCUX_ROOT}"; \
    cd "${MCUX_ROOT}"; \
    /opt/venv/bin/west init \
        -m https://github.com/nxp-mcuxpresso/mcuxsdk-manifests.git mcuxpresso-sdk; \
    cd "${MCUX_ROOT}/mcuxpresso-sdk"; \
    for board in ${MCUX_BOARDS}; do \
        sed -i '/se_hostlib\|emwin/d' "manifests/boards/${board}.yml"; \
        /opt/venv/bin/west update_board --set board "${board}"; \
    done; \
    git clone --depth 1 https://github.com/nxp-mcuxpresso/CMSIS_5.git \
        "${MCUX_ROOT}/CMSIS_5"; \
    if [ "${MCUX_PRUNE}" = "1" ]; then \
        rm -rf "${MCUXPRESSO}/docs" "${MCUXPRESSO}/middleware" "${MCUXPRESSO}/rtos"; \
        find "${MCUXPRESSO}/examples" -mindepth 1 -maxdepth 1 \
            ! -name '_boards' -exec rm -rf {} +; \
    fi; \
    find "${MCUX_ROOT}" -name .git -type d -prune -exec rm -rf {} +; \
    rm -rf /root/.cache

# Fail the build here rather than three months later in a wolfBoot CI job: a
# board whose fetch silently did nothing leaves a tree that looks fine until
# some target needs it. Covers the shared headers, each board's device tree
# and project_template, and the CMSIS core header.
RUN set -eux; \
    test -f "${MCUXPRESSO}/drivers/common/fsl_common.h"; \
    test -f "${MCUXPRESSO}/drivers/puf/fsl_puf.h"; \
    test -f "${MCUXPRESSO_CMSIS}/Core/Include/core_cm33.h"; \
    test -d "${MCUXPRESSO}/devices/LPC/LPC5500/LPC55S69"; \
    test -d "${MCUXPRESSO}/devices/MCX/MCXN/MCXN947"; \
    test -d "${MCUXPRESSO}/examples/_boards/lpcxpresso55s69/project_template"; \
    test -d "${MCUXPRESSO}/examples/_boards/frdmmcxn947/project_template"; \
    test -d "${MCUXPRESSO}/examples/_boards/mimxrt700evk"

# ---- m33mu: clone, build, install ----
RUN set -eux; \
    git clone --depth 1 https://github.com/danielinux/m33mu.git /tmp/m33mu; \
    cmake -S /tmp/m33mu -B /tmp/m33mu/build; \
    cmake --build /tmp/m33mu/build -j"$(nproc)"; \
    if [ -f /tmp/m33mu/build/m33mu ]; then \
      install -m 0755 /tmp/m33mu/build/m33mu /usr/local/bin/m33mu; \
    fi; \
    rm -rf /tmp/m33mu

WORKDIR /workspace
