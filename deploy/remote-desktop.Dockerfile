# Build an ARM64 RDP installation bundle without changing the Jetson host.
# This is a build candidate, not a configured or validated remote desktop.
# Extract /opt/output from target "builder"; never run a server in this image.
ARG BASE_IMAGE=nvcr.io/nvidia/l4t-jetpack@sha256:d1c8e971ab994235840eacc31c4ef4173bf9156317b1bf8aabe7e01eb21b2a0e
FROM ${BASE_IMAGE} AS builder

SHELL ["/bin/bash", "-euo", "pipefail", "-c"]
ARG XRDP_REVISION=80c52879fead585d6347df5b3c587718adf8f5a5
ARG XORGXRDP_REVISION=c2d3cbafebe00be3221f985c06ef6b97f1c63790
ARG MAX_JOBS=4
ENV DEBIAN_FRONTEND=noninteractive GIT_TERMINAL_PROMPT=0

# All development packages are confined to the builder. Disable optional GPU,
# audio, drive forwarding and video-codec integrations for the first candidate.
RUN test "$(uname -m)" = aarch64 && \
    apt-get update && apt-get install -y --no-install-recommends \
      autoconf automake build-essential ca-certificates check git libcmocka-dev \
      file libpam0g-dev libssl-dev libtool libx11-dev libxfixes-dev libxrandr-dev \
      pkg-config xserver-xorg-dev && \
    rm -rf /var/lib/apt/lists/* && \
    mkdir -p /opt/src /opt/output/opt/b2-remote/share/build-metadata

# Git validates object hashes; the full commits and their submodule gitlinks
# select source. Record an additional SHA256 of each unmodified source archive.
RUN git init /opt/src/xrdp && \
    git -C /opt/src/xrdp remote add origin https://github.com/neutrinolabs/xrdp.git && \
    git -C /opt/src/xrdp fetch --depth 1 origin "${XRDP_REVISION}" && \
    git -C /opt/src/xrdp checkout --detach FETCH_HEAD && \
    test "$(git -C /opt/src/xrdp rev-parse HEAD)" = "${XRDP_REVISION}" && \
    git -C /opt/src/xrdp submodule update --init --recursive --depth 1 --jobs "${MAX_JOBS}" && \
    git -C /opt/src/xrdp submodule status --recursive > \
      /opt/output/opt/b2-remote/share/build-metadata/xrdp-submodules.txt && \
    ! grep -Eq '^[+-U]' /opt/output/opt/b2-remote/share/build-metadata/xrdp-submodules.txt && \
    git init /opt/src/xorgxrdp && \
    git -C /opt/src/xorgxrdp remote add origin https://github.com/neutrinolabs/xorgxrdp.git && \
    git -C /opt/src/xorgxrdp fetch --depth 1 origin "${XORGXRDP_REVISION}" && \
    git -C /opt/src/xorgxrdp checkout --detach FETCH_HEAD && \
    test "$(git -C /opt/src/xorgxrdp rev-parse HEAD)" = "${XORGXRDP_REVISION}" && \
    printf 'xrdp %s\nxorgxrdp %s\n' "${XRDP_REVISION}" "${XORGXRDP_REVISION}" > \
      /opt/output/opt/b2-remote/share/build-metadata/source-revisions.txt && \
    for component in xrdp xorgxrdp; do \
      git -C "/opt/src/${component}" archive --format=tar HEAD | sha256sum > \
        "/opt/output/opt/b2-remote/share/build-metadata/${component}-source-tree.sha256"; \
    done && \
    dpkg-query -W > /opt/output/opt/b2-remote/share/build-metadata/build-packages.txt && \
    pkg-config --modversion xorg-server > \
      /opt/output/opt/b2-remote/share/build-metadata/xorg-header-version.txt && \
    pkg-config --variable=moduledir xorg-server > \
      /opt/output/opt/b2-remote/share/build-metadata/build-xorg-module-path.txt

# Focal's Check 0.10 lacks assertion APIs used by the unmodified upstream tests.
# Build the same test-only library at an exact newer revision, outside the bundle.
ARG CHECK_REVISION=11970a7e112dfe243a2e68773f014687df2900e8
RUN git init /opt/src/check && \
    git -C /opt/src/check remote add origin https://github.com/libcheck/check.git && \
    git -C /opt/src/check fetch --depth 1 origin "${CHECK_REVISION}" && \
    git -C /opt/src/check checkout --detach FETCH_HEAD && \
    test "$(git -C /opt/src/check rev-parse HEAD)" = "${CHECK_REVISION}" && \
    cd /opt/src/check && autoreconf --install && \
    ./configure --prefix=/opt/check --disable-shared --disable-subunit --disable-build-docs && \
    make -j"${MAX_JOBS}" && make install && \
    PKG_CONFIG_PATH=/opt/check/lib/pkgconfig pkg-config --exact-version=0.15.2 check && \
    printf 'Check %s\n' "${CHECK_REVISION}" >> \
      /opt/output/opt/b2-remote/share/build-metadata/source-revisions.txt && \
    git archive --format=tar HEAD | sha256sum > \
      /opt/output/opt/b2-remote/share/build-metadata/check-source-tree.sha256

# Strict locations are essential: prefix alone does not prevent upstream from
# selecting /etc and /var. PAM is staged separately for explicit host review.
# Generated build-time keys are removed in the same layer and never exported.
RUN export PKG_CONFIG_PATH=/opt/check/lib/pkgconfig && \
    cd /opt/src/xrdp && \
    ./bootstrap && \
    ./configure --prefix=/opt/b2-remote --enable-strict-locations \
      --libdir=/opt/b2-remote/lib --sysconfdir=/opt/b2-remote/etc \
      --localstatedir=/opt/b2-remote/var \
      --with-socketdir=/run/b2-remote \
      --with-pamconfdir=/etc/pam.d --enable-pam-config=debian \
      --with-systemdsystemunitdir=/opt/b2-remote/share/systemd \
      --enable-painter --enable-rfxcodec \
      --disable-smartcard --disable-fuse --disable-x264 --disable-openh264 \
      --disable-jpeg --disable-tjpeg --disable-opus --disable-mp3lame \
      --disable-fdkaac --disable-rdpsndaudin --disable-vsock \
      --with-imlib2=no --with-freetype2=no --enable-tests 2>&1 | \
      tee /opt/output/opt/b2-remote/share/build-metadata/xrdp-configure-output.log && \
    ! grep -Eqi 'unrecognized option' /opt/output/opt/b2-remote/share/build-metadata/xrdp-configure-output.log && \
    cp config.log /opt/output/opt/b2-remote/share/build-metadata/xrdp-config.log && \
    make -j"${MAX_JOBS}" && \
    make check > /opt/output/opt/b2-remote/share/build-metadata/xrdp-tests.log 2>&1 && \
    make DESTDIR=/opt/output install && \
    rm -f /opt/output/opt/b2-remote/etc/xrdp/rsakeys.ini \
      /opt/output/opt/b2-remote/etc/xrdp/cert.pem \
      /opt/output/opt/b2-remote/etc/xrdp/key.pem

# This adds modules for the pre-existing Xorg ABI, not a replacement X server.
# --enable-strict-locations avoids writing into /usr/lib/xorg/modules or /etc.
RUN cd /opt/src/xorgxrdp && \
    ./bootstrap && \
    ./configure --prefix=/opt/b2-remote --enable-strict-locations \
      --libdir=/opt/b2-remote/lib --sysconfdir=/opt/b2-remote/etc \
      --disable-glamor --without-simd XRDP_CFLAGS=-I/opt/src/xrdp/common 2>&1 | \
      tee /opt/output/opt/b2-remote/share/build-metadata/xorgxrdp-configure-output.log && \
    ! grep -Eqi 'unrecognized option' /opt/output/opt/b2-remote/share/build-metadata/xorgxrdp-configure-output.log && \
    cp config.log /opt/output/opt/b2-remote/share/build-metadata/xorgxrdp-config.log && \
    make -j"${MAX_JOBS}" && make DESTDIR=/opt/output install && \
    test -f /opt/output/opt/b2-remote/lib/xorg/modules/libxorgxrdp.so && \
    test -f /opt/output/opt/b2-remote/lib/xorg/modules/drivers/xrdpdev_drv.so && \
    test -f /opt/output/opt/b2-remote/etc/X11/xrdp/xorg.conf

# Keep the source notices, not a claim that the bundle inherits our MIT license.
# These are upstream license files in an untracked binary/build artifact only.
# Staged binaries still contain runtime paths to the final host prefix. Resolve
# their shared libraries from the staged tree for build checks only. Recheck
# linking on the host after installation; this is not a host-readiness test.
RUN export LD_LIBRARY_PATH=/opt/output/opt/b2-remote/lib/xrdp:/opt/output/opt/b2-remote/lib && \
    for component in xrdp xorgxrdp; do \
      cd "/opt/src/${component}"; \
      while IFS= read -r -d '' notice; do \
        destination="/opt/output/opt/b2-remote/share/licenses/${component}/${notice#./}"; \
        mkdir -p "$(dirname "$destination")"; cp "$notice" "$destination"; \
      done < <(find . -type d -name .git -prune -o -type f \
        \( -iname 'COPYING*' -o -iname 'LICENSE*' -o -iname 'NOTICE*' \) -print0); \
    done && \
    /opt/output/opt/b2-remote/sbin/xrdp --version > \
      /opt/output/opt/b2-remote/share/build-metadata/xrdp-version.txt 2>&1 && \
    for executable in /opt/output/opt/b2-remote/sbin/* \
                      /opt/output/opt/b2-remote/bin/* \
                      /opt/output/opt/b2-remote/libexec/xrdp/*; do \
      if test -f "$executable" && file "$executable" | grep -q 'ELF'; then \
        printf '\n%s\n' "$executable"; ldd "$executable"; \
      fi; \
    done > /opt/output/opt/b2-remote/share/build-metadata/executable-libraries.txt && \
    ! grep -q 'not found' /opt/output/opt/b2-remote/share/build-metadata/executable-libraries.txt && \
    readelf -d /opt/output/opt/b2-remote/lib/xorg/modules/libxorgxrdp.so > \
      /opt/output/opt/b2-remote/share/build-metadata/xorg-module-dynamic-section.txt && \
    test -z "$(find /opt/output -type f \( -name key.pem -o -name rsakeys.ini \) -print)" && \
    find /opt/output -type f -print0 | sort -z | xargs -0 sha256sum > /opt/bundle-files.sha256 && \
    cp /opt/bundle-files.sha256 /opt/output/opt/b2-remote/share/build-metadata/bundle-files.sha256

# Artifact-only stage: no shell, server command, listening port or host mutation.
# Classic Docker extraction: create without starting, then docker cp /opt/output.
FROM scratch AS bundle
COPY --from=builder /opt/output /opt/output
