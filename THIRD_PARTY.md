# Third-party materials

[日本語](THIRD_PARTY.ja.md)

These are references and optional runtime dependencies. Third-party code, models
and packages are not bundled. Explicit host/container setup installs external
software separately. Independent adapters call existing public APIs;
their mocked tests do not load the actual third-party runtimes. Review updated:
2026-10-27. Default-branch links may change; pin exact revisions before real-model
or hardware experiments.

| Material | Source | Current handling |
| --- | --- | --- |
| TIC-VLA paper | [arXiv, version 2](https://arxiv.org/abs/2602.02459v2) | Cite as the method's source; its results are not B2 validation |
| TIC-VLA software | [Repository](https://github.com/ucla-mobility/TIC-VLA) and [license at reviewed revision](https://github.com/ucla-mobility/TIC-VLA/blob/9fa6f8b66b9e121d5df5df071297bba8e5353ebb/LICENSE.md) | Academic Software License reviewed at `9fa6f8b`; source-only checkout outside the project for import checks; no source copied into this project |
| TIC-VLA checkpoint | [Official repository's linked checkpoint](https://huggingface.co/datasets/handsomeYun/TIC-VLA/blob/main/TIC-VLA-model.ckpt) | Not downloaded; verify applicable artifact terms before use |
| InternVL3-1B | [Model repository](https://huggingface.co/OpenGVLab/InternVL3-1B) | Candidate base model; terms and revision not yet reviewed for integration |
| Unitree SDK2 Python | [B2 client](https://github.com/unitreerobotics/unitree_sdk2_python/blob/master/unitree_sdk2py/b2/sport/sport_client.py), [BSD-3-Clause license](https://github.com/unitreerobotics/unitree_sdk2_python/blob/814556d15970dd2ecf1c9984e845ca02ab07e206/LICENSE) | API inspected; license reviewed at `814556d`; runtime revision, dependencies, and firmware compatibility remain unverified |

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
| ZED SDK / Python binding | [Official capture tutorial](https://docs.stereolabs.com/docs/tutorials/image-capture), [Jetson Docker guide](https://docs.stereolabs.com/docs/integrations/docker/install-on-nvidia-jetson) | Optional `pyzed.sl` calls; no SDK, driver, image, or vendor model bundled. Check the selected SDK/image terms before installation or sharing |
| PyTorch | [Official documentation](https://docs.pytorch.org/docs/stable/index.html) | Optional checkpoint loading and inference; not installed or bundled. Select a Jetson-compatible build and record its license/notices |
| Transformers / InternVL runtime | [Transformers documentation](https://huggingface.co/docs/transformers/index), [InternVL3-1B](https://huggingface.co/OpenGVLab/InternVL3-1B) | Optional upstream model loaders; local-only resolution. Trusted model Python code still executes; pin source and artifact revisions |
| Livox driver | [Official driver](https://github.com/Livox-SDK/livox_ros_driver2) | Reference only; not an implemented dependency and no source bundled |
| Base container image | [NVIDIA Jetson resources](https://developer.nvidia.com/embedded/jetson-cloud-native/), [publisher's JetPack EULA](https://docs.nvidia.com/jetson/jetpack/eula/index.html) | Matching-L4T base pulled for local Orin use; Python stage built. Image and component notices remain applicable; no binary image is bundled or published |

The standard-library replay and tests need no vendor runtime. Packaging declares
`setuptools>=68` as its build tool; running from `PYTHONPATH=src` needs no package
build or install. No vendor code has been copied into the independent adapters.
Installing dependencies later can introduce additional transitive requirements;
this table is not a completed redistribution audit or permission to publish them.

## Optional host management and Python tooling

Tailscale is used for the verified host-management SSH path, not bundled with the
application. Its Linux client source uses [BSD-3-Clause](https://github.com/tailscale/tailscale/blob/main/LICENSE);
tailnet enrollment, hosted-service terms and lab access rules are separate.
Use the [official installer](https://tailscale.com/docs/install/linux). SSH over
Tailscale is verified on the target; the exact client version remains uninspected.
[pyenv](https://github.com/pyenv/pyenv) is optional per-user interpreter tooling
under its [MIT license](https://github.com/pyenv/pyenv/blob/master/LICENSE), not a
bundled dependency or GPU-runtime sandbox. Neither tool is installed by this
Python package. Host setup uses official pyenv `v2.8.14` at
`3fb25668b463ad38ac2db6092dbf476ef744c0ca`, outside Git.
[CPython 3.11.18](https://www.python.org/downloads/release/python-31118/)
is installed per user under the [PSF License Agreement and included notices](https://github.com/python/cpython/blob/v3.11.18/LICENSE).
No interpreter binary is redistributed. See [runtime setup](docs/jetson-runtime.md).
Review updated for these references: 2026-10-27.
