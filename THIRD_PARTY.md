# Third-party materials

[日本語](THIRD_PARTY.ja.md)

These are references and prospective dependencies. None is bundled or installed
by this repository. Review date: 2026-10-22. Links to default branches may change;
pin exact revisions before implementation.

| Material | Source | Current handling |
| --- | --- | --- |
| TIC-VLA paper | [arXiv, version 2](https://arxiv.org/abs/2602.02459v2) | Cite as the method's source; its results are not B2 validation |
| TIC-VLA software | [Repository](https://github.com/ucla-mobility/TIC-VLA) and [license](https://github.com/ucla-mobility/TIC-VLA/blob/main/LICENSE.md) | Read for feasibility; no source copied into this project |
| TIC-VLA checkpoint | [Official repository's linked checkpoint](https://huggingface.co/datasets/handsomeYun/TIC-VLA/blob/main/TIC-VLA-model.ckpt) | Not downloaded; verify applicable artifact terms before use |
| InternVL3-1B | [Model repository](https://huggingface.co/OpenGVLab/InternVL3-1B) | Candidate base model; terms and revision not yet reviewed for integration |
| Unitree SDK2 Python | [B2 client](https://github.com/unitreerobotics/unitree_sdk2_python/blob/master/unitree_sdk2py/b2/sport/sport_client.py) | API inspected; package license, revision, and firmware compatibility remain to be checked |

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

The license and rights holder for original work in this project remain undecided.
No dependency's license should be copied as the license for this whole repository.
