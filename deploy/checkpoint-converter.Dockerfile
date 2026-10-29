# CPU-only checkpoint tools, separate from the older Jetson GPU Torch image.
# Pass the inspected local Python-stage image ID as BASE_IMAGE for a real build.
ARG BASE_IMAGE=vln-b2-python:jp5
FROM ${BASE_IMAGE}

RUN /opt/python/bin/python3.11 -m venv /opt/converter
COPY deploy/converter-requirements.lock /opt/runtime-metadata/converter-requirements.lock
RUN /opt/python/bin/python3.11 -m pip --python /opt/converter install \
      --no-cache-dir --only-binary=:all: --require-hashes \
      --report /opt/runtime-metadata/converter-install-report.json \
      -r /opt/runtime-metadata/converter-requirements.lock && \
    /opt/converter/bin/python -m pip check && \
    /opt/converter/bin/python -m pip freeze --all > /opt/runtime-metadata/converter-freeze.txt
ENV PATH=/opt/converter/bin:/opt/python/bin:${PATH} \
    PYTHONDONTWRITEBYTECODE=1 \
    HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 HF_DATASETS_OFFLINE=1
RUN python -c 'import torch, safetensors, numpy; assert torch.__version__ == "2.15.0+cpu"; assert torch.version.cuda is None; assert not torch.cuda.is_available(); print(torch.__version__, safetensors.__version__, numpy.__version__)'
COPY LICENSE THIRD_PARTY.md /opt/runtime-metadata/
WORKDIR /opt
CMD ["python", "-c", "import torch, safetensors; print(torch.__version__, safetensors.__version__)"]
