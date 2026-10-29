# Isolated SDK2 state-receive preparation; no Torch, models, robot or host changes.
# For deployment, pass the inspected local Python-stage image ID as BASE_IMAGE.
ARG BASE_IMAGE=vln-b2-python:jp5
FROM ${BASE_IMAGE}

ARG CYCLONEDDS_REVISION=9995905bce6c4cf9f740d6438bbf7fcfd1c83dfd
ARG UNITREE_REVISION=814556d15970dd2ecf1c9984e845ca02ab07e206
ENV PATH=/opt/unitree/bin:/opt/python/bin:${PATH} \
    CYCLONEDDS_HOME=/opt/cyclonedds \
    LD_LIBRARY_PATH=/opt/cyclonedds/lib \
    PYTHONDONTWRITEBYTECODE=1 PYTHONNOUSERSITE=1 \
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1

RUN test "$(uname -m)" = aarch64 && \
    /opt/python/bin/python3.11 -c 'import pathlib, sys, sysconfig; assert sys.version_info[:2] == (3, 11); assert (pathlib.Path(sysconfig.get_path("include")) / "Python.h").is_file()' && \
    /opt/python/bin/python3.11 -m venv /opt/unitree && \
    mkdir -p /opt/runtime-metadata/unitree/licenses /opt/vendor
COPY deploy/unitree-requirements.lock /opt/runtime-metadata/unitree-requirements.lock
# Bootstrap every binary requirement before building the C/Python extensions.
RUN /opt/python/bin/python3.11 -c 'from pathlib import Path; source=Path("/opt/runtime-metadata/unitree-requirements.lock"); Path("/opt/runtime-metadata/unitree-binary-requirements.lock").write_text("\n".join(line for line in source.read_text().splitlines() if not line.startswith("cyclonedds @")) + "\n")' && \
    /opt/python/bin/python3.11 -m pip --python /opt/unitree install \
      --no-cache-dir --only-binary=:all: --require-hashes \
      --report /opt/runtime-metadata/unitree-binary-install-report.json \
      -r /opt/runtime-metadata/unitree-binary-requirements.lock

RUN git init /opt/vendor/cyclonedds && cd /opt/vendor/cyclonedds && \
    git remote add origin https://github.com/eclipse-cyclonedds/cyclonedds.git && \
    git fetch --depth 1 origin "${CYCLONEDDS_REVISION}" && \
    git checkout --detach FETCH_HEAD && \
    test "$(git rev-parse HEAD)" = "${CYCLONEDDS_REVISION}" && \
    printf '%s\n' "${CYCLONEDDS_REVISION}" > /opt/runtime-metadata/unitree/cyclonedds-core-revision.txt && \
    cmake -S . -B /opt/build/cyclonedds \
      -DCMAKE_INSTALL_PREFIX=/opt/cyclonedds -DCMAKE_INSTALL_LIBDIR=lib \
      -DCMAKE_BUILD_TYPE=Release -DBUILD_EXAMPLES=OFF -DBUILD_TESTING=OFF \
      -DBUILD_DDSPERF=OFF -DENABLE_SSL=OFF -DENABLE_SECURITY=OFF -DENABLE_SHM=OFF && \
    cmake --build /opt/build/cyclonedds --target install --parallel 2 && \
    cp LICENSE /opt/runtime-metadata/unitree/licenses/cyclonedds-core-LICENSE && \
    cp /opt/build/cyclonedds/CMakeCache.txt /opt/runtime-metadata/unitree/cyclonedds-CMakeCache.txt
# The sdist is hash checked; build isolation is disabled to use the pinned tools.
RUN /opt/unitree/bin/python -m pip install --no-cache-dir --no-build-isolation \
      --no-deps --require-hashes \
      --report /opt/runtime-metadata/unitree-python-install-report.json \
      -r /opt/runtime-metadata/unitree-requirements.lock

RUN git init /opt/vendor/unitree_sdk2_python && cd /opt/vendor/unitree_sdk2_python && \
    git remote add origin https://github.com/unitreerobotics/unitree_sdk2_python.git && \
    git fetch --depth 1 origin "${UNITREE_REVISION}" && \
    git checkout --detach FETCH_HEAD && \
    test "$(git rev-parse HEAD)" = "${UNITREE_REVISION}" && \
    printf '%s\n' "${UNITREE_REVISION}" > /opt/runtime-metadata/unitree/unitree-sdk2-revision.txt && \
    cp LICENSE /opt/runtime-metadata/unitree/licenses/unitree-sdk2-LICENSE && \
    PIP_NO_INDEX=1 /opt/unitree/bin/python -m pip install \
      --no-cache-dir --no-deps --no-build-isolation \
      --report /opt/runtime-metadata/unitree-sdk2-install-report.json . && \
    /opt/unitree/bin/python -m pip check && \
    /opt/unitree/bin/python -m pip freeze --all > /opt/runtime-metadata/unitree-freeze.txt && \
    dpkg-query -W > /opt/runtime-metadata/unitree-debian-packages.txt
# Preserve full installed metadata and every bundled license/notice, including
# NumPy/OpenCV binary component notices. Vendor source trees retain originals too.
RUN /opt/unitree/bin/python -c 'import importlib.metadata as m, json, pathlib, shutil; root=pathlib.Path("/opt/runtime-metadata/unitree"); distributions=list(m.distributions()); (root / "python-distributions.json").write_text(json.dumps([{"name": d.metadata["Name"], "version": d.version, "license": d.metadata.get("License"), "license_expression": d.metadata.get("License-Expression"), "requires": d.requires or []} for d in distributions], indent=2) + "\n"); metadata=[(d, f) for d in distributions for f in (d.files or []) if ".dist-info" in str(f) or any(token in str(f).lower() for token in ("license", "copying", "notice", "copyright"))]; [(target.parent.mkdir(parents=True, exist_ok=True), shutil.copy2(d.locate_file(f), target)) for d, f in metadata if pathlib.Path(d.locate_file(f)).is_file() for target in [root / "python-notices" / d.metadata["Name"] / str(f).replace("..", "_parent_")]]'
COPY LICENSE THIRD_PARTY.md /opt/runtime-metadata/
COPY tools/verify_unitree_sdk.py /opt/runtime-tools/verify_unitree_sdk.py
WORKDIR /opt
# Run explicitly with --network none and a writable private report mount.
# Build completion is not a robot connectivity or firmware compatibility check.
CMD ["python", "/opt/runtime-tools/verify_unitree_sdk.py", "--help"]
