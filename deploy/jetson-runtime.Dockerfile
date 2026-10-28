# Model-free build candidate for the inspected L4T 35.4.1 / CUDA 11.4 host.
# Build target "python" first; target "runtime" compiles Torch and torchvision.
# This old Torch candidate must not load external checkpoints. See the runtime guide.
ARG BASE_IMAGE=nvcr.io/nvidia/l4t-jetpack@sha256:d1c8e971ab994235840eacc31c4ef4173bf9156317b1bf8aabe7e01eb21b2a0e
FROM ${BASE_IMAGE} AS python

ARG PYTHON_VERSION=3.11.18
ARG PYTHON_SHA256=9120e0a653868f6e3698d36cdd99e5a58903ec9469e448f21d98f7b16d8fa290
ARG MAX_JOBS=4
ENV DEBIAN_FRONTEND=noninteractive
RUN test "$(uname -m)" = aarch64 && \
    apt-get update && apt-get install -y --no-install-recommends \
      build-essential ca-certificates curl git libbz2-dev libffi-dev \
      libgdbm-dev libgdbm-compat-dev libjpeg-dev liblzma-dev libncursesw5-dev \
      libopenblas-dev libpng-dev libreadline-dev libsqlite3-dev libssl-dev \
      uuid-dev xz-utils zlib1g-dev && \
    rm -rf /var/lib/apt/lists/*
RUN mkdir -p /opt/build/python /opt/runtime-metadata && \
    curl --fail --location --retry 3 \
      "https://www.python.org/ftp/python/${PYTHON_VERSION}/Python-${PYTHON_VERSION}.tar.xz" \
      --output /opt/build/python/source.tar.xz && \
    echo "${PYTHON_SHA256}  /opt/build/python/source.tar.xz" | sha256sum --check --strict && \
    tar -xJf /opt/build/python/source.tar.xz -C /opt/build/python --strip-components=1 && \
    cd /opt/build/python && \
    ./configure --prefix=/opt/python --enable-shared --with-ensurepip=install && \
    make -j"${MAX_JOBS}" && make install && \
    printf '/opt/python/lib\n' > /etc/ld.so.conf.d/b2-python.conf && ldconfig && \
    /opt/python/bin/python3.11 -c 'import bz2, ctypes, lzma, sqlite3, ssl; print(ssl.OPENSSL_VERSION)' && \
    rm -rf /opt/build/python
ENV PATH=/opt/python/bin:/usr/local/cuda/bin:${PATH}
RUN python3.11 -m pip install --no-cache-dir \
      pip==25.2 setuptools==80.9.0 wheel==0.45.1 && \
    python3.11 --version && \
    dpkg-query -W > /opt/runtime-metadata/debian-packages.txt
COPY LICENSE THIRD_PARTY.md /opt/runtime-metadata/
COPY deploy/runtime-smoke.py /opt/runtime-smoke.py
ENV HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1
WORKDIR /opt
CMD ["python3.11", "/opt/runtime-smoke.py", "--stage", "python"]

FROM python AS runtime
ARG MAX_JOBS=4
ARG TORCH_REVISION=39901f229520a5256505ec24782f716ee7ddc843
ARG VISION_REVISION=c1d70fe1aa3f37ecdc809311f6c238df900dfd19
ENV CUDA_HOME=/usr/local/cuda \
    TORCH_CUDA_ARCH_LIST=8.7 \
    MAX_JOBS=${MAX_JOBS} \
    USE_CUDA=1 USE_CUDNN=1 USE_DISTRIBUTED=1 USE_GLOO=1 \
    USE_NCCL=0 USE_MPI=0 USE_TENSORPIPE=0 USE_FLASH_ATTENTION=0 \
    USE_MEM_EFF_ATTENTION=0 USE_CUSPARSELT=0 USE_KINETO=0 \
    USE_MKLDNN=0 USE_FBGEMM=0 USE_NNPACK=0 USE_QNNPACK=0 USE_XNNPACK=0 \
    BUILD_TEST=0 BUILD_CAFFE2=0 \
    PYTORCH_BUILD_VERSION=2.2.2 PYTORCH_BUILD_NUMBER=1
RUN python3.11 -m pip install --no-cache-dir \
      cmake==3.27.9 ninja==1.11.1.1 numpy==1.26.4 astunparse==1.6.3 \
      pyyaml==6.0.2 typing-extensions==4.12.2 sympy==1.12 networkx==3.2.1 \
      jinja2==3.1.6 fsspec==2024.6.1 filelock==3.16.1 packaging==24.2 \
      psutil==6.0.0 requests==2.32.4 optree==0.12.1 && \
    python3.11 -c 'import subprocess; version=subprocess.check_output(["gcc", "-dumpfullversion"], text=True).strip(); assert tuple(map(int, version.split(".")[:2])) >= (9, 4), version' && \
    /usr/local/cuda/bin/nvcc --version | grep 'release 11.4' && cmake --version
RUN mkdir -p /opt/build /opt/wheels && \
    git init /opt/build/pytorch && cd /opt/build/pytorch && \
    git remote add origin https://github.com/pytorch/pytorch.git && \
    git fetch --depth 1 origin "${TORCH_REVISION}" && \
    git checkout --detach FETCH_HEAD && \
    test "$(git rev-parse HEAD)" = "${TORCH_REVISION}" && \
    git submodule sync --recursive && \
    git submodule update --init --recursive --depth 1 --jobs "${MAX_JOBS}" && \
    git submodule status --recursive > /opt/runtime-metadata/torch-submodules.txt && \
    python3.11 setup.py bdist_wheel --dist-dir=/opt/wheels && \
    python3.11 -m pip install --no-index --no-deps /opt/wheels/torch-2.2.2-*.whl && \
    printf '%s\n' "${TORCH_REVISION}" > /opt/runtime-metadata/torch-revision.txt && \
    rm -rf /opt/build/pytorch
# Resume boundary: a verified completed Torch image may supply the layers above.
ENV FORCE_CUDA=1 BUILD_VERSION=0.17.2 PYTORCH_VERSION=2.2.2 \
    TORCHVISION_USE_FFMPEG=0 TORCHVISION_USE_VIDEO_CODEC=0 TORCHVISION_USE_NVJPEG=0
COPY deploy/disable-unused-torch-rpc.py /opt/runtime-tools/disable-unused-torch-rpc.py
COPY LICENSE THIRD_PARTY.md /opt/runtime-metadata/
COPY deploy/runtime-smoke.py /opt/runtime-smoke.py
RUN python3.11 /opt/runtime-tools/disable-unused-torch-rpc.py && \
    python3.11 -c 'import torch; import torch.distributed.rpc as rpc; assert torch.distributed.is_available(); assert not rpc.is_available()'
RUN python3.11 -m pip install --no-cache-dir pillow==10.4.0 && \
    git init /opt/build/vision && cd /opt/build/vision && \
    git remote add origin https://github.com/pytorch/vision.git && \
    git fetch --depth 1 origin "${VISION_REVISION}" && \
    git checkout --detach FETCH_HEAD && \
    test "$(git rev-parse HEAD)" = "${VISION_REVISION}" && \
    python3.11 setup.py bdist_wheel --dist-dir=/opt/wheels && \
    python3.11 -m pip install --no-index --no-deps /opt/wheels/torchvision-0.17.2-*.whl && \
    printf '%s\n' "${VISION_REVISION}" > /opt/runtime-metadata/vision-revision.txt && \
    rm -rf /opt/build/vision
COPY deploy/runtime-requirements.txt /opt/runtime-requirements.txt
RUN python3.11 -m pip install --no-cache-dir -r /opt/runtime-requirements.txt && \
    python3.11 -m pip uninstall --yes cmake ninja && \
    python3.11 -m pip check && \
    python3.11 -m pip freeze --all > /opt/runtime-metadata/python-packages.txt
CMD ["python3.11", "/opt/runtime-smoke.py", "--stage", "torch"]
