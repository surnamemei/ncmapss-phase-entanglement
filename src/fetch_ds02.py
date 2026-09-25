"""Download the DS02 HDF5 research copy from its Figshare record."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import requests


ARTICLE = "https://api.figshare.com/v2/articles/20436504"
CHUNK = 32 * 1024 * 1024


def fetch_part(url: str, start: int, end: int, path: Path) -> None:
    if path.exists() and path.stat().st_size == end - start + 1:
        return
    for attempt in range(5):
        try:
            response = requests.get(
                url, headers={"Range": f"bytes={start}-{end}"}, timeout=180
            )
            response.raise_for_status()
            if response.status_code != 206 or len(response.content) != end - start + 1:
                raise RuntimeError(f"Bad range response: {response.status_code}")
            path.write_bytes(response.content)
            return
        except (requests.RequestException, RuntimeError):
            if attempt == 4:
                raise


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("N-CMAPSS/N-CMAPSS_DS02-006.h5"))
    args = parser.parse_args()
    record = requests.get(ARTICLE, timeout=30).json()
    file = next(f for f in record["files"] if f["name"] == "N-CMAPSS_DS02-006.h5")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    parts = args.output.parent / "ds02_parts"
    parts.mkdir(exist_ok=True)
    ranges = [
        (i, i * CHUNK, min(file["size"], (i + 1) * CHUNK) - 1)
        for i in range((file["size"] + CHUNK - 1) // CHUNK)
    ]
    with ThreadPoolExecutor(max_workers=12) as pool:
        futures = [
            pool.submit(fetch_part, file["download_url"], start, end, parts / f"{i:04d}.part")
            for i, start, end in ranges
        ]
        for count, future in enumerate(as_completed(futures), 1):
            future.result()
            if count % 10 == 0 or count == len(futures):
                print(f"Downloaded {count}/{len(futures)} parts", flush=True)
    temporary = args.output.with_suffix(".h5.part")
    md5 = hashlib.md5()
    with temporary.open("wb") as target:
        for i, _, _ in ranges:
            with (parts / f"{i:04d}.part").open("rb") as source:
                while chunk := source.read(8 * 1024 * 1024):
                    md5.update(chunk)
                    target.write(chunk)
    actual = md5.hexdigest()
    if actual != file["computed_md5"] or temporary.stat().st_size != file["size"]:
        raise RuntimeError(f"Checksum/size mismatch: {actual}")
    os.replace(temporary, args.output)
    for i, _, _ in ranges:
        (parts / f"{i:04d}.part").unlink()
    parts.rmdir()
    provenance = {
        "article": ARTICLE,
        "doi": record["doi"],
        "download_url": file["download_url"],
        "size": file["size"],
        "md5": actual,
        "note": "Figshare research copy; NASA PCoE hosts the full N-CMAPSS archive",
    }
    (args.output.parent / "source.json").write_text(json.dumps(provenance, indent=2))
    print(f"Verified {args.output} MD5 {actual}", flush=True)


if __name__ == "__main__":
    main()
