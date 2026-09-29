"""Extract the unopened N-CMAPSS subsets from the local official NASA archive (bytes only).

Extension stage 1 (docs/extension/EXTENSION_CHARTER.md). The script copies HDF5 members out of the
nested official archive, checks every ZIP CRC-32 and size, and records MD5 and SHA-256. It never
opens an HDF5 file, so no sensor, operating or label value is read. Existing files are never
overwritten; the DS02/DS03 copies already in use are only verified against the archive directory.
"""

from __future__ import annotations

import hashlib
import json
import shutil
import sys
import time
import zipfile
import zlib
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "N-CMAPSS"
OUTER = DATA_DIR / "nasa_dataset2_official.zip"
OUTER_SIZE = 15760443389
OUTER_MEMBER = "17. Turbofan Engine Degradation Simulation Data Set 2/data_set.zip"
INNER = DATA_DIR / "data_set.zip"
RECORD = ROOT / "docs/extension/archive_extraction_record.json"
BLOCK = 8 << 20
ALREADY_OPENED = {"N-CMAPSS_DS02-006.h5", "N-CMAPSS_DS03-012.h5"}


def now_utc():
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")


def digests(path):
    md5, sha, crc = hashlib.md5(), hashlib.sha256(), 0
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(BLOCK), b""):
            md5.update(block)
            sha.update(block)
            crc = zlib.crc32(block, crc)
    return {"bytes": path.stat().st_size, "md5": md5.hexdigest(), "sha256": sha.hexdigest(),
            "crc32": f"{crc & 0xFFFFFFFF:08x}"}


def extract_member(archive, info, destination):
    """Copy one member to destination via a .partial file; ZipExtFile verifies the CRC-32 at EOF."""
    if destination.exists():
        raise FileExistsError(f"Refusing to overwrite {destination}")
    partial = destination.with_name(destination.name + ".partial")
    if partial.exists():
        raise FileExistsError(f"Refusing to overwrite {partial}")
    try:
        with archive.open(info) as source, partial.open("wb") as output:
            shutil.copyfileobj(source, output, length=BLOCK)
        if partial.stat().st_size != info.file_size:
            raise RuntimeError(f"Extracted size differs from the ZIP directory: {info.filename}")
        partial.replace(destination)
    except Exception:
        partial.unlink(missing_ok=True)
        raise


def main():
    if RECORD.exists():
        raise FileExistsError(f"Extraction already recorded: {RECORD}")
    if OUTER.stat().st_size != OUTER_SIZE:
        raise RuntimeError("Official NASA archive has an unexpected size")
    record = {"started_utc": now_utc(), "outer_archive": OUTER.name, "outer_bytes": OUTER_SIZE,
              "outer_member": OUTER_MEMBER, "hdf5_opened": False,
              "note": "Bytes copied and CRC/size-checked only; no HDF5 file was opened by this script."}
    clock = time.time()
    if not INNER.exists():
        with zipfile.ZipFile(OUTER) as outer:
            info = outer.getinfo(OUTER_MEMBER)
            record["inner_zip_directory"] = {"bytes": info.file_size, "crc32": f"{info.CRC:08x}"}
            print(f"Extracting nested archive ({info.file_size} bytes)", flush=True)
            extract_member(outer, info, INNER)
    record["inner_zip_extract_seconds"] = round(time.time() - clock, 1)
    members = []
    with zipfile.ZipFile(INNER) as inner:
        for info in inner.infolist():
            members.append({"name": info.filename, "bytes": info.file_size,
                            "compressed_bytes": info.compress_size, "crc32": f"{info.CRC:08x}",
                            "date_time": list(info.date_time)})
        record["inner_members"] = members
        files = {}
        for info in inner.infolist():
            name = Path(info.filename).name
            if not name.endswith(".h5"):
                continue
            destination = DATA_DIR / name
            entry = {"member": info.filename, "zip_bytes": info.file_size, "zip_crc32": f"{info.CRC:08x}"}
            if name in ALREADY_OPENED:
                if not destination.exists():
                    raise FileNotFoundError(destination)
                entry["action"] = "verified existing project copy (already opened by the frozen study)"
            else:
                clock = time.time()
                print(f"Extracting {info.filename}", flush=True)
                extract_member(inner, info, destination)
                entry["action"] = "extracted (bytes only)"
                entry["extract_seconds"] = round(time.time() - clock, 1)
            entry.update(digests(destination))
            if entry["bytes"] != info.file_size or entry["crc32"] != f"{info.CRC:08x}":
                raise RuntimeError(f"Local copy differs from the official ZIP directory: {name}")
            files[name] = entry
            print(f"{name}: {entry['bytes']} bytes, CRC {entry['crc32']}, SHA-256 {entry['sha256']}", flush=True)
    record["hdf5_files"] = files
    record["finished_utc"] = now_utc()
    RECORD.parent.mkdir(parents=True, exist_ok=True)
    with RECORD.open("x", encoding="utf-8") as stream:
        json.dump(record, stream, indent=2)
    print(f"Record written: {RECORD}", flush=True)


if __name__ == "__main__":
    sys.exit(main())
