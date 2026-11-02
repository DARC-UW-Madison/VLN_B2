# Third-party materials

[日本語](THIRD_PARTY.ja.md)

These are references and optional runtime dependencies. Third-party code, models
and packages are not bundled. Explicit host/container setup installs external
software separately. Independent adapters call existing public APIs;
their mocked tests do not load the actual third-party runtimes. Review updated:
2026-10-29. Default-branch links may change; pin exact revisions before real-model
or hardware experiments.

| Material | Source | Current handling |
| --- | --- | --- |
| TIC-VLA paper | [arXiv, version 2](https://arxiv.org/abs/2602.02459v2) | Cite as the method's source; its results are not B2 validation |
| TIC-VLA software | [Repository](https://github.com/ucla-mobility/TIC-VLA) and [license at reviewed revision](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/LICENSE.md) | Academic Software License reviewed at `9fa6f8b`; source-only checkout outside the project for import checks; no source copied into this project |
| TIC-VLA checkpoint | [Official repository's linked checkpoint](https://huggingface.co/datasets/handsomeYun/TIC-VLA/blob/671de608f39ccae41b66cbb24ab923c0275f8fb4/TIC-VLA-model.ckpt) | Approved pinned payload acquired and CPU-converted privately; source terms remain applicable |
| InternVL3-1B | [Model repository](https://huggingface.co/OpenGVLab/InternVL3-1B) | Pinned approved snapshot acquired and code-reviewed for isolated loading; model-card/component terms and notices retained |
| Unitree SDK2 Python | [B2 client](https://github.com/unitreerobotics/unitree_sdk2_python/blob/master/unitree_sdk2py/b2/sport/sport_client.py), [BSD-3-Clause license](https://github.com/unitreerobotics/unitree_sdk2_python/blob/814556d15970dd2ecf1c9984e845ca02ab07e206/LICENSE) | Pinned source `814556d` imported only for state/IDL in a separate local image; offline import/serialization passed; full SDK dependency declaration is not satisfied and real B2 compatibility remains unverified |

The inspected TIC-VLA software license permits specified educational or academic
research use by academic or nonprofit researchers and prohibits onward transfer
of the software, including derivatives. Research use is not permission to
publish adapted upstream code. Resolve the applicable permission before use or
sharing; this repository does not grant it. Read the full upstream terms.

The checkpoint hosting page displays a dataset-level license label. Record the
terms applicable to the specific weights and their dependencies rather than
assuming that label overrides the software license or covers every artifact.

For each dependency actually adopted, add its exact revision, license source,
use in the project, whether anything is redistributed, required notices, and
the outcome of the review. Keep restricted artifacts in approved storage.

The [MIT License](LICENSE) covers this project's original code and documentation
only. It does not relicense dependencies, upstream software, model weights or
data, and no dependency's license is adopted as the license for this repository.

## Future research and sharing

Independently written adapters, evaluation tools and documentation may remain
under MIT. Modified upstream code, converted or fine-tuned weights, datasets and
recordings require a separate release decision based on their source terms and
applicable research agreements. Training or conversion does not by itself remove
upstream restrictions. Publish methods and original contributions without
assuming permission to redistribute restricted artifacts. Keep unpublished
results and identifying recordings in approved laboratory storage.

## Preparation-tool dependencies

| Material | Source | Use and distribution |
|---|---|---|
| ZED SDK / Python binding | [Official capture tutorial](https://docs.stereolabs.com/docs/tutorials/image-capture), [Jetson Docker guide](https://docs.stereolabs.com/docs/integrations/docker/install-on-nvidia-jetson) | Existing SDK 4.1.2 reused read-only; official pyzed 4.1 MIT wheel and Cython 3.0.12 Apache-2.0 verified privately; import/capture passed. No SDK, wheel, driver, image or vendor model bundled; native SDK terms remain separate |
| PyTorch | [Official documentation](https://docs.pytorch.org/docs/stable/index.html) | Torch 2.2.2 at `39901f2` built locally under its BSD-style license and included third-party notices. Local image disables unused Python RPC with a hash-checked feature guard; original wheel/license/NOTICE retained. Not bundled with repository source or host venv; approved safetensors loading passed, original pickle loading remains blocked |
| Transformers / InternVL runtime | [Transformers documentation](https://huggingface.co/docs/transformers/index), [InternVL3-1B](https://huggingface.co/OpenGVLab/InternVL3-1B) | Optional upstream model loaders; local-only resolution. Trusted model Python code still executes; pin source and artifact revisions |
| Livox driver | [Official driver](https://github.com/Livox-SDK/livox_ros_driver2) | Reference only; not an implemented dependency and no source bundled |
| Base container image | [NVIDIA Jetson resources](https://developer.nvidia.com/embedded/jetson-cloud-native/), [publisher's JetPack EULA](https://docs.nvidia.com/jetson/jetpack/eula/index.html) | Matching-L4T base pulled for local Orin use; Python stage built. Image and component notices remain applicable; no binary image is bundled or published |

The standard-library replay and tests need no vendor runtime. Packaging declares
`setuptools>=68` as its build tool; running from `PYTHONPATH=src` needs no package
build or install. No vendor code has been copied into the independent adapters.
Installing dependencies later can introduce additional transitive requirements;
this table is not a completed redistribution audit or permission to publish them.

## Remote-desktop build candidate

The optional management build is separate from the model runtime. The
[recipe](deploy/remote-desktop.Dockerfile) pins xrdp 0.10.6.1 at
`80c52879fead585d6347df5b3c587718adf8f5a5` under
[Apache-2.0 and included third-party terms](https://raw.githubusercontent.com/neutrinolabs/xrdp/80c52879fead585d6347df5b3c587718adf8f5a5/COPYING),
and xorgxrdp 0.10.5 at `c2d3cbafebe00be3221f985c06ef6b97f1c63790` under
[its X11-style permissive terms](https://raw.githubusercontent.com/neutrinolabs/xorgxrdp/c2d3cbafebe00be3221f985c06ef6b97f1c63790/COPYING).
Do not substitute our MIT notice or assert an unverified SPDX identifier for the
latter. Git-pinned optional submodules retain their notices. The bundle preserves
COPYING/LICENSE/NOTICE files; it is a local artifact, not a published image.
[Check 0.15.2](https://github.com/libcheck/check/tree/11970a7e112dfe243a2e68773f014687df2900e8)
is a test-only build dependency under its LGPL-2.1 terms; it is not linked into
or bundled with the exported RDP runtime. The builder's other OS packages retain
their own terms. This is not a full binary-redistribution clearance.

Existing NoMachine 8.20.1-5 was discovered on the target; it was not installed,
modified or bundled by this project. Its commercial/vendor conditions are
separate from this source repository. No license or client-access entitlement is
inferred from package presence. See [RDP build details](docs/rdp-build.md).

## Optional host management and Python tooling

Tailscale is used for the verified host-management SSH path, not bundled with the
application. Its Linux client source uses [BSD-3-Clause](https://github.com/tailscale/tailscale/blob/main/LICENSE);
tailnet enrollment, hosted-service terms and lab access rules are separate.
Use the [official installer](https://tailscale.com/docs/install/linux). SSH over
Tailscale was verified on the target; the inspected client/daemon version is
1.104.4 after the controlled 2026-10-28 update. Review access details in the
remote-desktop guide.
[pyenv](https://github.com/pyenv/pyenv) is optional per-user interpreter tooling
under its [MIT license](https://github.com/pyenv/pyenv/blob/master/LICENSE), not a
bundled dependency or GPU-runtime sandbox. Neither tool is installed by this
Python package. Host setup uses official pyenv `v2.8.14` at
`3fb25668b463ad38ac2db6092dbf476ef744c0ca`, outside Git.
[CPython 3.11.18](https://www.python.org/downloads/release/python-31118/)
is installed per user under the [PSF License Agreement and included notices](https://github.com/python/cpython/blob/v3.11.18/LICENSE).
No interpreter binary is redistributed. See [runtime setup](docs/jetson-runtime.md).
Review updated for these references: 2026-10-27.

## CPU conversion candidate

`deploy/converter-requirements.lock` pins 12 Python 3.11/aarch64 CPU-converter
packages and their official wheel SHA256 values. Torch 2.15.0+cpu is selected
from the [official CPU index](https://download.pytorch.org/whl/cpu/torch/), not
the CUDA-enabled PyPI artifact. The remaining exact files were reviewed through
[official PyPI metadata](https://pypi.org/): filelock/setuptools (MIT),
typing-extensions (PSF-2.0), SymPy/mpmath/NetworkX/Jinja/MarkupSafe/fsspec
(BSD-family), safetensors (Apache-2.0), and NumPy (its published
BSD-3-Clause/0BSD/MIT/Zlib/CC0-1.0 expression). Preserve bundled binary/component
notices; those summaries do not relicense the wheels. The recipe isolates these
packages in a new container venv, with no model data or upstream TIC-VLA source.
The pinned container build, `pip check`, generated checkpoint conversion and
old-runtime readback passed. The approved actual checkpoint was subsequently
converted and loaded privately; this repository distributes neither payload. No converter image or third-party wheel is released by this repository.

## State-receive SDK environment

The [state-only recipe](deploy/unitree-state.Dockerfile) fixes Unitree source at
`814556d15970dd2ecf1c9984e845ca02ab07e206` (BSD-3-Clause) and CycloneDDS C core at
`9995905bce6c4cf9f740d6438bbf7fcfd1c83dfd` / Python 0.10.2. Both DDS components
allow EPL-2.0 or EDL-1.0; this local build selects EDL-1.0 and retains original
notices: [C core](https://github.com/eclipse-cyclonedds/cyclonedds/blob/0.10.2/LICENSE),
[Python](https://github.com/eclipse-cyclonedds/cyclonedds-python/blob/0.10.2/LICENSE).
The hash-pinned lock records twelve software/build artifacts. CMake is a
separate build-only environment. SDK source/setup/license hashes are preserved;
no SDK wheel is installed and its full NumPy/OpenCV dependency declaration is
explicitly unsatisfied. The narrow state path passed an offline synthetic
serialization test. Other SDK features and physical B2 compatibility need review.
No vendor source, wheel or resulting binary image is distributed here. See
[build provenance and limits](docs/unitree-runtime.md).
