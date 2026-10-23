# Select an existing image compatible with the inspected Jetson L4T installation.
# No base image, vendor SDK, PyTorch build, or model version is guessed here.
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
WORKDIR /opt/b2-tic-vla
COPY pyproject.toml README.md ./
COPY src/ src/
COPY examples/ examples/
ENV PYTHONPATH=/opt/b2-tic-vla/src
ENTRYPOINT ["python3", "-m", "b2_tic_vla"]
CMD ["--help"]
