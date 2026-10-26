"""独立验证生成的真寻包；仅标准库，不导入或启动插件。"""

import argparse
import hashlib
import json
from pathlib import Path, PurePosixPath
import stat
from zipfile import ZipFile

ROOT_NAME = "zhenxun_plugin_farm_preview"
MANIFEST = "FARM-MANIFEST.json"
MAX_BYTES = 100 * 1024 * 1024


def safe_path(name):
    path = PurePosixPath(name)
    if (not name or "\\" in name or ":" in name or path.is_absolute()
            or any(part in (".", "..", "") for part in name.split("/"))
            or path.as_posix() != name):
        raise ValueError("Unsafe package path")
    return path


def verify_files(files):
    if MANIFEST not in files or len(files[MANIFEST]) > 1024 * 1024:
        raise ValueError("Missing or oversized manifest")
    manifest = json.loads(files[MANIFEST])
    if (manifest.get("schema") != 1 or manifest.get("target") != "zhenxun"
            or manifest.get("plugin") != ROOT_NAME):
        raise ValueError("Invalid package identity")
    expected = manifest["files"]
    if (not isinstance(expected, dict)
            or set(files) != set(expected) | {MANIFEST}):
        raise ValueError("Package files differ from manifest")
    for name, digest in expected.items():
        safe_path(name)
        if hashlib.sha256(files[name]).hexdigest() != digest:
            raise ValueError("Package checksum mismatch")
    required = {"__init__.py", "runtime.py", "commands.py", "requirements.txt",
                "LICENSE", "_vendor/farm_core/__init__.py",
                "_vendor/farm_render/data/asset-manifest.json",
                "_vendor/farm_render/data/font-manifest.json",
                "_vendor/farm_render/data/OFL-Xiaolai.txt"}
    if any(name.endswith('/assets.zip') for name in files):
        raise ValueError('Resource ZIP must not be in plugin repository')
    if not required <= set(files):
        raise ValueError("Incomplete plugin")
    return manifest


def read_package(path):
    with ZipFile(path) as archive:
        items = archive.infolist()
        names = [item.filename for item in items]
        if (len(names) != len(set(names)) or len(names) > 200
                or sum(item.file_size for item in items) > MAX_BYTES):
            raise ValueError("Duplicate paths or package too large")
        files = {}
        for item in items:
            name = safe_path(item.filename)
            if (len(name.parts) < 2 or name.parts[0] != ROOT_NAME
                    or item.is_dir()
                    or stat.S_ISLNK(item.external_attr >> 16)):
                raise ValueError("Unexpected package root or link")
            files[name.relative_to(ROOT_NAME).as_posix()] = archive.read(item)
    verify_files(files)
    return files


def verify_package(path):
    return verify_files(read_package(path))


def verify_directory(directory):
    directory = Path(directory).resolve()
    files = {}
    for path in directory.rglob("*"):
        relative = path.relative_to(directory)
        if any(part in (".git", "__pycache__") for part in relative.parts):
            continue
        if path.is_symlink():
            raise ValueError("Unexpected symbolic link")
        if path.is_file():
            files[relative.as_posix()] = path.read_bytes()
    return verify_files(files)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("package", nargs="?", type=Path)
    parser.add_argument("--directory", type=Path)
    args = parser.parse_args()
    if bool(args.package) == bool(args.directory):
        parser.error("Choose a ZIP or --directory")
    manifest = (verify_directory(args.directory) if args.directory
                else verify_package(args.package))
    print(f"Verified zhenxun {manifest['version']}: "
          f"{len(manifest['files'])} files")


if __name__ == "__main__":
    main()
