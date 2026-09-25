"""Extract official DS03 from NASA's N-CMAPSS archive via HTTP byte ranges."""

from __future__ import annotations

import hashlib
import shutil
import zipfile
from pathlib import Path


ARCHIVE = (
    "https://phm-datasets.s3.amazonaws.com/NASA/"
    "17.+Turbofan+Engine+Degradation+Simulation+Data+Set+2.zip"
)
OUTER_MEMBER = "17. Turbofan Engine Degradation Simulation Data Set 2/data_set.zip"
MEMBER = "data_set/N-CMAPSS_DS03-012.h5"
DEST = Path(__file__).resolve().parents[1] / "N-CMAPSS/N-CMAPSS_DS03-012.h5"
LOCAL_ARCHIVE = DEST.parent / "nasa_dataset2_official.zip"
BLOCK = 8 * 1024 * 1024


def main():
    if DEST.exists():
        raise FileExistsError(f"Refusing to overwrite {DEST}")
    if LOCAL_ARCHIVE.stat().st_size != 15760443389:
        raise RuntimeError("Official NASA archive is incomplete")
    inner_path = DEST.parent / "data_set.zip.partial"
    if inner_path.exists():
        raise FileExistsError(f"Refusing to overwrite {inner_path}")
    with zipfile.ZipFile(LOCAL_ARCHIVE) as archive:
        info = archive.getinfo(OUTER_MEMBER)
        print(
            f"Nested ZIP: {info.filename}; uncompressed={info.file_size}; "
            f"CRC32={info.CRC:08x}",
            flush=True,
        )
        DEST.parent.mkdir(parents=True, exist_ok=True)
        with archive.open(info) as source, inner_path.open("wb") as output:
            shutil.copyfileobj(source, output, length=BLOCK)
    with zipfile.ZipFile(inner_path) as archive:
        info = archive.getinfo(MEMBER)
        print(f"DS03 member: {info.filename}; bytes={info.file_size}; CRC32={info.CRC:08x}", flush=True)
        temporary = DEST.with_suffix(".h5.partial")
        if temporary.exists():
            raise FileExistsError(f"Refusing to overwrite {temporary}")
        try:
            with archive.open(info) as source, temporary.open("wb") as output:
                shutil.copyfileobj(source, output, length=BLOCK)
            if temporary.stat().st_size != info.file_size:
                raise RuntimeError("Extracted size does not match official ZIP directory")
            temporary.replace(DEST)
        except Exception:
            temporary.unlink(missing_ok=True)
            raise
    digest = hashlib.md5()
    with DEST.open("rb") as stream:
        for block in iter(lambda: stream.read(BLOCK), b""):
            digest.update(block)
    print(f"DS03 saved: {DEST}; MD5={digest.hexdigest()}", flush=True)


if __name__ == "__main__":
    main()
