# Isolated Unitree state-receive environment

[日本語](unitree-runtime.ja.md) · [Documentation](../README.md) · [Field network](../how-to/field-network.md)

> Document type: **Reference**.

## Purpose and boundary

Prepare the software needed to receive B2 state before the robot visit. The
recipe builds a separate ARM64/Python 3.11 image from the already inspected
Jetson Python stage. It changes neither host Python/ROS nor the tested GPU
image. No Torch, model weights, camera or motion service is added.

The offline verifier imports the native DDS library and SDK state definitions,
then serializes/deserializes synthetic state. It never initializes the SDK
channel factory, a DDS participant or a robot client. Network isolation is an
external Docker precondition, not something a Python flag proves. Passing it
does not prove B2 firmware/topic/domain/QoS compatibility or authorize motion.

## Pinned inputs and licenses

| Component | Fixed input |
|---|---|
| Local Python base | `sha256:7bf4dcefa6ffc9448f910caa9192e559502062aa742baf8d10b95f6931c7381e` |
| CycloneDDS C core | 0.10.2, commit `9995905bce6c4cf9f740d6438bbf7fcfd1c83dfd` |
| CycloneDDS Python | 0.10.2, hash-checked source archive in the lock |
| Unitree SDK2 Python | Source revision `814556d15970dd2ecf1c9984e845ca02ab07e206`, original declared version 1.0.1 |
| Other software/build tools | Twelve exact artifacts total in `deploy/unitree-requirements.lock` |

The SDK uses [BSD-3-Clause](https://github.com/unitreerobotics/unitree_sdk2_python/blob/814556d15970dd2ecf1c9984e845ca02ab07e206/LICENSE).
CycloneDDS C/Python offer EPL-2.0 or EDL-1.0; use the EDL option with its notices
retained. See the [C core license](https://github.com/eclipse-cyclonedds/cyclonedds/blob/0.10.2/LICENSE)
and [Python license](https://github.com/eclipse-cyclonedds/cyclonedds-python/blob/0.10.2/LICENSE).
These components are not relicensed by this repository's MIT license. Vendor
source, build metadata and installed notices remain in the private image; this
repository distributes only its original recipe/verifier, not a binary image.

## Why the SDK is a source import

The full SDK's unchanged setup declaration requires CycloneDDS, NumPy and
OpenCV. The state channel/IDL path needs CycloneDDS and the standard library.
This image deliberately imports the pinned SDK source via `PYTHONPATH` instead
of installing the full SDK distribution. NumPy/OpenCV and unrelated image/video
components are not added. Do not claim that the full SDK's declared dependencies
are satisfied. `pip check` covers the installed CycloneDDS environment only.
Other SDK features need separate dependency/API review.

The verifier explicitly records `sdk_import_mode="pinned source; state path only"`
and `declared_full_sdk_dependencies_satisfied=false`. It rejects an installed
SDK distribution mixed into that environment. It verifies source origin, exact
detached revision, original setup/license hashes, every Python source hash and
setup AST literals without executing setup.py. The native library path and
`/proc/self/maps` must both select the dedicated `/opt/cyclonedds` prefix.

## Build on Jetson

Use [the recipe](../../deploy/unitree-state.Dockerfile) and inspect the existing base
image first. The following is a Jetson command, not a Mac setup step:

```sh
sudo env DOCKER_BUILDKIT=0 docker build --pull=false \
  --memory 4g --cpu-period 100000 --cpu-quota 200000 \
  --build-arg BASE_IMAGE=sha256:7bf4dcefa6ffc9448f910caa9192e559502062aa742baf8d10b95f6931c7381e \
  -f deploy/unitree-state.Dockerfile -t vln-b2-unitree:jp5 .
```

The inspected host lacked the buildx plugin, so this uses its existing legacy
builder. It does not install a new builder on either computer. CMake compiles
the C core with two jobs into `/opt/cyclonedds`; examples/tests/ddsperf and
optional SSL/security/SHM components are disabled in this isolated candidate,
not in host ROS/network policy. The Python binding builds from the pinned
source archive against that prefix. CMake is in `/opt/sdk-build-tools`, separate
from `/opt/unitree` runtime metadata.

The first candidate built the core, Python binding and SDK wheel, then failed
`pip check` on CMake 3.27.9's WHEEL metadata. Its executable worked; compatible
tags were present after a blank header separator. This is retained as a failed
attempt, not a successful environment. The revised recipe separates the
build-only tool and imports only the SDK state source. It does not edit vendor
metadata or skip runtime dependency checks. Exact commands, logs and exit codes
are private under `local/unitree-build`.

Build records include pinned revisions, full original licenses, CMake cache,
runtime/build-tool freezes, package install reports, Debian inventory and SDK
source manifests under `/opt/runtime-metadata`. Do not publish/share the image
merely because its recipe is in Git.

## Offline acceptance

After a successful build, choose a new private report directory:

```sh
mkdir -m 700 local/unitree-check-01
sudo docker run --rm --pull never --runtime runc --network none --read-only \
  --user "$(id -u):$(id -g)" --cap-drop ALL --security-opt no-new-privileges \
  --memory 1g --cpus 2 --pids-limit 64 --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  --mount "type=bind,src=$(pwd)/local/unitree-check-01,dst=/reports" \
  --entrypoint /opt/unitree/bin/python vln-b2-unitree:jp5 \
  /opt/runtime-tools/verify_unitree_sdk.py --report /reports/unitree-sdk-offline.json
```

Keep Docker invocation/image ID alongside the JSON. Do not set
`CYCLONEDDS_PYTHON_NO_IMPORT_LIBS`: bypassing native loading defeats this check.
Reports are created 0600 without overwriting an existing file or symlink.
The verifier stores errors as failures instead of silently changing pins.

## Verified local result

See the separate [record](../records/sdk-build-checks.md) for the result and history.

## First robot connection

Keep B2 disconnected until the [field procedure](../how-to/field-network.md) establishes
the cable/port, subnet, unused address, interface, domain and recovery path.
Then run the project's state subscriber with the explicit confirmed interface
and domain, using source mounts/PYTHONPATH for both this project and the pinned
SDK. That is a separate receive-only network test: DDS discovery/subscription
traffic is sent, but no motor command is sent. Confirm real message fields,
units, axes and timing before pairing state with camera images. Control
authority, remote-controller priority, command loss and stopping remain later
acceptance steps. Connecting Ethernet alone does not finish deployment.

### Prepared receive-only command

After confirming the field network, substitute the actual wired `IFACE` and
lab `DOMAIN_ID` below. This command is a **template, not an executed robot test**.
Unlike the offline verifier, it uses `--network host` to reach the robot LAN;
SDK initialization selects the explicit interface. Preserve management Wi-Fi
and do not bridge/NAT the robot LAN to campus. Read state statistics and actual
finite samples; exit code zero alone does not prove messages were received.
Reported frame identifiers remain unknown until measured. Use a new output
folder and record the exact image ID and command next to its report.

```sh
mkdir -m 700 local/state-visit-01
sudo docker run --rm --pull never --runtime runc --network host --read-only \
  --user "$(id -u):$(id -g)" --cap-drop ALL --security-opt no-new-privileges \
  --memory 1g --cpus 2 --pids-limit 64 --tmpfs /tmp:rw,nosuid,nodev,size=64m \
  --mount "type=bind,src=$(pwd)/src,dst=/workspace/src,readonly" \
  --mount "type=bind,src=$(pwd)/local/state-visit-01,dst=/reports" \
  -e HOME=/tmp -e PYTHONPATH=/workspace/src:/opt/vendor/unitree_sdk2_python \
  --entrypoint timeout vln-b2-unitree:jp5 -k 5s 15s \
  /opt/unitree/bin/python -m b2_tic_vla state \
  --interface IFACE --domain-id DOMAIN_ID --seconds 3 --output /reports/state.json
```
