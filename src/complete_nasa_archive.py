"""Finish an interrupted official NASA archive download using parallel byte ranges."""

from __future__ import annotations

import os
import shutil
import time
import urllib.request
import zipfile
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path


URL = (
    "https://phm-datasets.s3.amazonaws.com/NASA/"
    "17.+Turbofan+Engine+Degradation+Simulation+Data+Set+2.zip"
)
SIZE = 15760443389
DEST = Path(__file__).resolve().parents[1] / "N-CMAPSS/nasa_dataset2_official.zip"
COMPLETE = DEST.with_name("nasa_dataset2_official_complete.zip")
PART_DIR = DEST.parent / "nasa_dataset2_parts"
PART_SIZE = 512 * 1024 * 1024
WORKERS = 12


def fetch_part(index, start, end):
    path = PART_DIR / f"part_{index:03d}"
    expected = end - start + 1
    for attempt in range(6):
        current = path.stat().st_size if path.exists() else 0
        if current == expected:
            return path
        if current > expected:
            raise RuntimeError(f"Range part is too large: {path}")
        begin = start + current
        request = urllib.request.Request(
            URL, headers={"Range": f"bytes={begin}-{end}"}
        )
        try:
            with urllib.request.urlopen(request, timeout=120) as response:
                if response.status != 206:
                    raise RuntimeError(f"Expected HTTP 206, got {response.status}")
                if response.headers.get("Content-Range") != f"bytes {begin}-{end}/{SIZE}":
                    raise RuntimeError("NASA byte-range response did not match request")
                with path.open("ab") as output:
                    shutil.copyfileobj(response, output, length=8 * 1024 * 1024)
            if path.stat().st_size == expected:
                print(f"Range {index} complete: {expected} bytes", flush=True)
                return path
        except Exception as error:
            print(f"Range {index} attempt {attempt + 1}: {error}", flush=True)
        time.sleep(min(2 ** attempt, 20))
    raise RuntimeError(f"Range {index} could not be completed")


def main():
    if DEST.stat().st_size >= SIZE:
        raise RuntimeError("Official NASA archive is already complete")
    prefix = DEST.stat().st_size
    PART_DIR.mkdir(parents=True, exist_ok=True)
    ranges = []
    for index, start in enumerate(range(prefix, SIZE, PART_SIZE)):
        ranges.append((index, start, min(start + PART_SIZE, SIZE) - 1))
    print(f"Existing prefix: {prefix} bytes; downloading {len(ranges)} ranges", flush=True)
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        jobs = [pool.submit(fetch_part, *item) for item in ranges]
        for job in as_completed(jobs):
            job.result()
    if COMPLETE.exists():
        raise FileExistsError(f"Refusing to overwrite {COMPLETE}")
    with COMPLETE.open("wb") as output, DEST.open("rb") as source:
        shutil.copyfileobj(source, output, length=8 * 1024 * 1024)
        for index, _, _ in ranges:
            with (PART_DIR / f"part_{index:03d}").open("rb") as part:
                shutil.copyfileobj(part, output, length=8 * 1024 * 1024)
    if COMPLETE.stat().st_size != SIZE:
        raise RuntimeError("Assembled archive has the wrong size")
    with zipfile.ZipFile(COMPLETE) as archive:
        names = archive.namelist()
        if not any(name.endswith("data_set.zip") for name in names):
            raise RuntimeError("Official archive ZIP directory is invalid")
    os.replace(COMPLETE, DEST)
    for index, _, _ in ranges:
        (PART_DIR / f"part_{index:03d}").unlink()
    PART_DIR.rmdir()
    print(f"Official archive complete: {DEST}; {SIZE} bytes", flush=True)


if __name__ == "__main__":
    main()
