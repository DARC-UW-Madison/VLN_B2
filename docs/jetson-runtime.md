# Jetson runtime setup

[日本語](jetson-runtime.ja.md) · [Status](status.md) · [Compatibility](runtime-compatibility.md)

This guide separates the host tools from the model container. The host remains
Ubuntu 20.04 / L4T 35.4.1 with its existing CUDA, ROS and ZED installation.
No robot connection or model file is needed for these steps.

## Host workspace and Python

The reviewed source archive is on the external Jetson at
`~/Developer/Projects/Robotics/b2/VLN_B2`. It contains no Git credentials or
copied virtual environment. Work from that directory. The dedicated login uses:

| Location | Purpose |
|---|---|
| `~/Developer/External/pyenv` | Official pyenv source, pinned to `3fb25668b463ad38ac2db6092dbf476ef744c0ca` (`v2.8.14`) |
| `~/Developer/Environments/pyenv` | Per-user interpreter installations |
| `.venv/` | This project's Python dependencies; outside Git |
| `local/` | Build output, logs and private inspection records; outside Git |

[CPython 3.11.18](https://www.python.org/downloads/release/python-31118/) is the
installed host application interpreter. The official
[pyenv build definition](https://github.com/pyenv/pyenv/blob/3fb25668b463ad38ac2db6092dbf476ef744c0ca/plugins/python-build/share/python-build/3.11.18)
verifies its source archive checksum. Python 3.10 has reached end of support;
the package minimum is not the version to choose for a new environment.
The host build adds only `libbz2-dev`, `libncurses-dev` and `libreadline-dev`;
the package transaction upgrades or removes nothing. System Python and shell
startup files are not replaced. The source build is limited to four jobs.

For a fresh account on the inspected host, the corresponding setup is below.
Stop if either pyenv location already exists; do not replace an existing tool.

```sh
sudo apt-get install -y --no-upgrade --no-install-recommends libbz2-dev libreadline-dev
mkdir -p "$HOME/Developer/External" "$HOME/Developer/Environments" local/python-build/tmp
git clone --depth 1 --branch v2.8.14 https://github.com/pyenv/pyenv.git \
  "$HOME/Developer/External/pyenv"
test "$(git -C "$HOME/Developer/External/pyenv" rev-parse HEAD)" = \
  3fb25668b463ad38ac2db6092dbf476ef744c0ca && \
  env PYENV_ROOT="$HOME/Developer/Environments/pyenv" \
    PYTHON_BUILD_MIRROR_URL_SKIP=1 MAKE_OPTS=-j4 \
    TMPDIR="$PWD/local/python-build/tmp" \
    "$HOME/Developer/External/pyenv/bin/pyenv" install 3.11.18
```

After the per-user interpreter build completes, create the project environment
only if `.venv` does not already exist:

```sh
"$HOME/Developer/Environments/pyenv/versions/3.11.18/bin/python3" -m venv .venv
PYTHONPATH=src .venv/bin/python -m b2_tic_vla replay
PYTHONPATH=src .venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m pip install --no-deps -e .
.venv/bin/b2-tic-vla --help
```

This environment runs the independent project tools. It does not install
PyTorch, ZED bindings or Unitree SDK, and does not prove their compatibility.
On 2026-10-27 the interpreter's compression, SSL, SQLite, ctypes and readline
imports passed, and all 85 project tests plus synthetic replay passed in this
Jetson venv. These tests still use mocked vendor interfaces.
Editable package installation, CLI help and `pip check` also passed.

An administrator-only read of the existing ZED SDK headers reports **4.1.2**;
the shared library and binding installer are present. The installation directory
is mode `0770` and inaccessible to the research login. No permission was changed.
Resolve access or a compatible isolated sensor environment when connecting the
camera; header presence does not establish working capture or Python bindings.

## Native CUDA check

The independent check allocates three small GPU buffers, computes
`output = 2 * x + y` for 256 FP32 elements, synchronizes, and compares every
element with the CPU result. It is neither a benchmark nor a model test.

```sh
mkdir -p local/native-smoke
timeout -k 5s 60s /usr/local/cuda/bin/nvcc -O2 -arch=sm_87 \
  deploy/cuda-smoke.cu -o local/native-smoke/cuda-smoke
timeout -k 5s 30s ./local/native-smoke/cuda-smoke
```

On 2026-10-27 this passed on the external Jetson: compute capability 8.7,
driver/runtime API 11040, and maximum absolute error 0. The same binary also
passed inside the pinned NVIDIA base container with `--runtime=nvidia` and
`--network=none`. BF16/PyTorch operations and navigation remain unverified.

## Storage prerequisite

The existing 2 TB SSD contains about 1 TB of allocated data. A non-writing
inspection used `ro,noload,nodev,nosuid,noexec`; roughly 946 GB was available
to an ordinary user. The superblock reports `needs_recovery`. The
[kernel documentation](https://docs.kernel.org/admin-guide/ext4.html) explains
that even an ordinary read-only ext4 mount can replay the journal; `noload`
prevents that replay. After explicit operator permission, a normal writable
mount replayed the journal successfully; no ext4 error was observed. A new
`/mnt/b2-research/VLN_B2` directory preserves the previous contents.

The storage procedure is:

1. Establish ownership and backup/recovery arrangements for the existing data.
   Obtain explicit permission for journal recovery and a writable mount.
2. Mount normally, without formatting or deleting data, then create a new
   dedicated directory such as `/mnt/b2-research/VLN_B2`. Stop on filesystem
   errors rather than forcing a mount or running automatic repair.
3. Recheck that Docker has no containers, images or volumes. Preserve its old
   data root and back up its configuration. Add an SSD mount entry using the
   locally verified filesystem identity; keep identities outside Git.
4. Put the new Docker data root in the dedicated SSD directory. Preserve NVIDIA
   runtime settings. Add a service mount dependency and mountpoint check so a
   missing SSD cannot silently fill the root filesystem. Validate configuration,
   restart Docker, and verify storage and runtime registration. Restore the
   saved configuration if validation fails; preserve both stores.

Before relocation Docker had no containers, images or volumes. Its data root
is now `/mnt/b2-research/VLN_B2/docker`; NVIDIA runtime registration and
approximately 20 GB free on the OS filesystem were verified after restart.
The old store remains intact. Configuration backups are
`/etc/docker/daemon.json.before-vln-b2` and `/etc/fstab.before-vln-b2`; the guard
is `/etc/systemd/system/docker.service.d/vln-b2-storage.conf`. No account group
was changed and no reboot has been performed. The standard
`~/.cache/huggingface` points to a new empty SSD directory; no model was fetched.

## Container build and model-free checks

The prepared Dockerfile uses an exact matching-L4T base digest and pinned
Python/Torch/torchvision sources. The Python stage built and passed its offline
check: Python 3.11.18, ARM64 and one visible CUDA device. The full Torch stage
is a separate source-build candidate. Direct dependency
pins are not a complete transitive lock; successful builds record Debian and
Python package inventories inside the image. Keep resolved image IDs and logs
in local experiment records.

After establishing storage, build the smaller Python stage first:

```sh
sudo docker build --target python -f deploy/jetson-runtime.Dockerfile \
  -t vln-b2-python:jp5 .
sudo docker run --rm --pull=never --runtime=nvidia --network=none \
  vln-b2-python:jp5
sudo docker build --target runtime -f deploy/jetson-runtime.Dockerfile \
  -t vln-b2-runtime:jp5 .
sudo docker run --rm --pull=never --runtime=nvidia --network=none \
  vln-b2-runtime:jp5
```

The first check requires Python 3.11 and a visible CUDA driver/device. The second
checks Torch/vision versions and actual FP32/BF16 GPU operations. Neither loads
models. The optional `--stage full` also imports a pinned upstream checkout
mounted read-only, without constructing a model; review its terms first.
Do not mount cameras, robot devices, model caches or Docker sockets for these checks.

The source-only upstream checkout is outside the project at
`~/Developer/External/TIC-VLA`, pinned to
`9fa6f8b66b9e121d5df5df071297bba8e5353ebb`. Sparse checkout selects the Python
package, license and package metadata only. No model blob was selected. Once
the Torch checks pass, run the optional import check with that reviewed source:

```sh
sudo docker run --rm --pull=never --runtime=nvidia --network=none \
  --mount type=bind,source="$HOME/Developer/External/TIC-VLA",target=/opt/upstream,readonly \
  vln-b2-runtime:jp5 python3.11 /opt/runtime-smoke.py \
  --stage full --upstream-root /opt/upstream
```

**Checkpoint loading remains blocked in this old-Torch candidate.** Resolve the
published loading vulnerabilities or validate a separate conversion/loading
path before using external weights. Model acquisition separately requires exact
files, revisions, terms, sizes and official-cache location; no weights have been
downloaded. See the [compatibility constraints](runtime-compatibility.md).
