"""Compare the project DS02 file with the member in NASA's official archive."""

from __future__ import annotations

import hashlib
import json
import os
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests

from fetch_ds02 import fetch_part


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "N-CMAPSS"
URL = "https://phm-datasets.s3.amazonaws.com/NASA/17.+Turbofan+Engine+Degradation+Simulation+Data+Set+2.zip"
CHUNK = 64 * 1024 * 1024


def copy_hash(source, target=None):
    digest = hashlib.md5()
    while chunk := source.read(8 * 1024 * 1024):
        digest.update(chunk)
        if target is not None:
            target.write(chunk)
    return digest.hexdigest()


def main():
    size = int(requests.head(URL, timeout=60).headers["Content-Length"])
    parts = DATA_DIR / "official_parts"
    parts.mkdir(exist_ok=True)
    ranges = [(i, i * CHUNK, min(size, (i + 1) * CHUNK) - 1)
              for i in range((size + CHUNK - 1) // CHUNK)]
    with ThreadPoolExecutor(max_workers=24) as pool:
        futures = [pool.submit(fetch_part, URL, start, end, parts / f"{i:04d}.part")
                   for i, start, end in ranges]
        for count, future in enumerate(as_completed(futures), 1):
            future.result()
            if count % 20 == 0 or count == len(futures):
                print(f"NASA archive: {count}/{len(futures)} parts", flush=True)
    outer = DATA_DIR / "official_archive.zip"
    with outer.open("wb") as target:
        for i, _, _ in ranges:
            with (parts / f"{i:04d}.part").open("rb") as source:
                while chunk := source.read(8 * 1024 * 1024):
                    target.write(chunk)
    assert outer.stat().st_size == size
    for i, _, _ in ranges:
        (parts / f"{i:04d}.part").unlink()
    parts.rmdir()
    inner = DATA_DIR / "official_inner.zip"
    with zipfile.ZipFile(outer) as archive:
        candidates = [m for m in archive.infolist() if m.filename.endswith("data_set.zip")]
        assert len(candidates) == 1, [m.filename for m in archive.infolist()]
        with archive.open(candidates[0]) as source, inner.open("wb") as target:
            copy_hash(source, target)
    print("Extracted nested official archive", flush=True)
    with zipfile.ZipFile(inner) as archive:
        candidates = [m for m in archive.infolist() if "DS02" in m.filename and m.filename.endswith(".h5")]
        assert len(candidates) == 1, [m.filename for m in candidates]
        member = candidates[0]
        print(f"Official member: {member.filename} ({member.file_size} bytes)", flush=True)
        with archive.open(member) as source:
            nasa_md5 = copy_hash(source)
    project = DATA_DIR / "N-CMAPSS_DS02-006.h5"
    with project.open("rb") as source:
        project_md5 = copy_hash(source)
    result = {"nasa_archive_url": URL, "nasa_archive_bytes": size,
              "official_member": member.filename, "official_member_bytes": member.file_size,
              "official_member_md5": nasa_md5, "project_md5": project_md5,
              "identical": nasa_md5 == project_md5 and member.file_size == project.stat().st_size}
    (DATA_DIR / "official_verification.json").write_text(json.dumps(result, indent=2))
    print(json.dumps(result, indent=2), flush=True)
    if not result["identical"]:
        raise RuntimeError("Project file differs from NASA archive member")
    os.unlink(outer)
    os.unlink(inner)


if __name__ == "__main__":
    main()
