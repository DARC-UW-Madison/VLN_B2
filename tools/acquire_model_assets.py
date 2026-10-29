"""Show the pinned plan, or fetch explicitly approved files with the official Hub client.

Use --download only after the operator approves the exact plan and applicable
terms. This program hashes data but never imports or executes model code.
"""

import argparse
import hashlib
import importlib
import json
from pathlib import Path

BASE_FILES = {
    "README.md": 35849, "added_tokens.json": 790, "config.json": 6326,
    "configuration_intern_vit.py": 5548, "configuration_internvl_chat.py": 4036,
    "conversation.py": 15309, "generation_config.json": 69, "merges.txt": 1671853,
    "model.safetensors": 1876463472, "modeling_intern_vit.py": 18099,
    "modeling_internvl_chat.py": 15971, "preprocessor_config.json": 287,
    "special_tokens_map.json": 613, "tokenizer.json": 7033297,
    "tokenizer_config.json": 7330, "vocab.json": 3383407,
}
PLAN = [
    {"repository": "handsomeYun/TIC-VLA", "repository_type": "dataset",
     "revision": "671de608f39ccae41b66cbb24ab923c0275f8fb4",
     "files": {"TIC-VLA-model.ckpt": 1938501547},
     "sha256": {"TIC-VLA-model.ckpt": "376263f89fad0f42c267d85655019232edc91d36e214e23424804dd4cd42e036"}},
    {"repository": "OpenGVLab/InternVL3-1B", "repository_type": "model",
     "revision": "4415a3b810e636d11dfa86b0e9ba40bb00535aa8", "files": BASE_FILES,
     "sha256": {"model.safetensors": "a8b67c54568417f3631723e6b3e120720eaa638e03e62dc25666c70e3ae3e484"}},
]


def plan_summary():
    return {"plan": PLAN, "total_files": sum(len(item["files"]) for item in PLAN),
            "total_bytes": sum(sum(item["files"].values()) for item in PLAN)}


def verify_file(path, expected_bytes, expected_sha256=None, expected_git_blob=None):
    if path.stat().st_size != expected_bytes:
        raise ValueError("Acquired file size differs from the approved plan.")
    sha = hashlib.sha256()
    blob = hashlib.sha1(b"blob " + str(expected_bytes).encode() + b"\0")
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            sha.update(chunk)
            if expected_git_blob:
                blob.update(chunk)
    if expected_sha256 and sha.hexdigest() != expected_sha256:
        raise ValueError("Acquired file SHA256 differs from the approved plan.")
    if expected_git_blob and blob.hexdigest() != expected_git_blob:
        raise ValueError("Acquired Git blob differs from pinned repository metadata.")
    if not expected_sha256 and not expected_git_blob:
        raise ValueError("No expected digest was available; acquisition is not verified.")
    return sha.hexdigest()


def acquire(cache, report):
    cache, report = Path(cache), Path(report)
    if report.exists() or report.is_symlink():
        raise FileExistsError("Use a new acquisition report; existing reports are retained.")
    if not cache.is_dir() or not report.parent.is_dir():
        raise ValueError("Prepare the dedicated cache and report directories first.")
    hub = importlib.import_module("huggingface_hub")
    api = hub.HfApi(token=False)
    inventory = []
    for item in PLAN:
        info = api.repo_info(item["repository"], repo_type=item["repository_type"],
                             revision=item["revision"], files_metadata=True, token=False)
        if info.sha != item["revision"]:
            raise ValueError("Repository metadata does not match the approved revision.")
        siblings = {entry.rfilename: entry for entry in info.siblings}
        for name, size in item["files"].items():
            entry = siblings[name]
            if entry.size != size:
                raise ValueError("Pinned metadata size differs from the approved plan.")
            expected = item["sha256"].get(name)
            lfs = entry.lfs or {}
            lfs_sha = lfs.get("sha256") if isinstance(lfs, dict) else getattr(lfs, "sha256", None)
            if expected and lfs_sha != expected:
                raise ValueError("Pinned LFS metadata differs from the approved SHA256.")
            if not expected and not entry.blob_id:
                raise ValueError("Pinned metadata has no Git blob digest.")
            path = Path(hub.hf_hub_download(
                item["repository"], name, repo_type=item["repository_type"],
                revision=item["revision"], cache_dir=str(cache), token=False,
                local_files_only=False,
            ))
            digest = verify_file(path, size, expected, None if expected else entry.blob_id)
            inventory.append({"repository": item["repository"], "repository_type": item["repository_type"],
                              "revision": item["revision"], "filename": name, "bytes": size,
                              "sha256": digest, "pinned_git_blob": entry.blob_id,
                              "cache_path": str(path)})
            print(json.dumps({"verified_files": len(inventory), "filename": name,
                              "verified_bytes": sum(row["bytes"] for row in inventory)}), flush=True)
    result = {"verified": True, "client_version": str(hub.__version__), "files": inventory,
              "total_bytes": sum(row["bytes"] for row in inventory), "model_code_executed": False}
    if result["total_bytes"] != plan_summary()["total_bytes"]:
        raise ValueError("Acquisition total differs from the approved plan.")
    with report.open("x") as stream:
        json.dump(result, stream, indent=2)
        stream.write("\n")
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--download", action="store_true")
    parser.add_argument("--cache", help="Mounted standard Hub cache directory; no token file is needed")
    parser.add_argument("--report", help="A new private report path outside Git")
    args = parser.parse_args(argv)
    if not args.download:
        print(json.dumps(plan_summary(), indent=2))
        return
    if not args.cache or not args.report:
        parser.error("--download requires --cache and --report.")
    acquire(args.cache, args.report)


if __name__ == "__main__":
    main()
