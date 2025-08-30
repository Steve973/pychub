from __future__ import annotations

import shutil
import subprocess
import sys
import zipfile
from email.parser import Parser
from pathlib import Path

from .constants import (
    CHUB_BUILD_DIR,
    CHUB_LIBS_DIR,
    CHUB_SCRIPTS_DIR,
    CHUBCONFIG_FILENAME,
    RUNTIME_DIR,
    CHUB_POST_INSTALL_SCRIPTS_DIR,
    CHUB_PRE_INSTALL_SCRIPTS_DIR,
    CHUB_BUILD_DIR_STRUCTURE,
    CHUB_INCLUDES_DIR)
from ..model.chubconfig_model import ChubConfig, Scripts


def create_chub_archive(chub_build_dir: Path, chub_archive_path: Path) -> Path:
    with zipfile.ZipFile(chub_archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in sorted(chub_build_dir.rglob("*"), key=lambda p: p.relative_to(chub_build_dir).as_posix()):
            if file_path.resolve() == Path(chub_archive_path).resolve():
                continue
            arcname = file_path.relative_to(chub_build_dir)
            zf.write(file_path, arcname)
    return chub_archive_path


def copy_runtime_files(chub_build_dir: Path) -> None:
    candidates = [
        Path(__file__).resolve().parent.parent / RUNTIME_DIR,  # src/pychubby/runtime
        Path(__file__).resolve().parent / RUNTIME_DIR,         # src/pychubby/package/runtime (legacy)
    ]
    runtime_src = next((p for p in candidates if p.exists()), None)
    if runtime_src is None:
        tried = " | ".join(str(p) for p in candidates)
        raise FileNotFoundError(
            f"Runtime directory not found. Looked in: {tried}")

    runtime_dst = chub_build_dir / RUNTIME_DIR
    shutil.copytree(runtime_src, runtime_dst, dirs_exist_ok=True)

    # Ensure archive runs via `python test_pkg.chub`
    chub_main_py = chub_build_dir / "__main__.py"
    chub_main_py.write_text(
        f"import runpy; runpy.run_module('{RUNTIME_DIR}', run_name='__main__')",
        encoding="utf-8")


def copy_included_files(chub_base: Path, included_files: list[str] | []) -> None:
    if not included_files:
        return

    for item in included_files:
        if "::" in item:
            src_str, dest_str = item.split("::", 1)
        else:
            src_str, dest_str = item, ""

        src = Path(src_str).expanduser().resolve()
        if not src.is_file():
            raise FileNotFoundError(f"Included file not found: {src_str}")

        includes_dir = chub_base / CHUB_INCLUDES_DIR
        dest_path = (includes_dir / dest_str).resolve() if dest_str else (includes_dir / src.name).resolve()

        # Prevent directory traversal
        if not str(dest_path).startswith(str(includes_dir)):
            raise ValueError(f"Destination '{dest_path}' escapes chub includes directory '{includes_dir}'")

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest_path)


def copy_install_scripts(
    scripts_base: Path,
    install_scripts: list[tuple[Path, str]] | [],
    scripts_type: str) -> None:
    if not install_scripts:
        return

    script_base = scripts_base / scripts_type
    for item in install_scripts:
        path, name = item
        src = Path(path).expanduser().resolve()
        if not src.is_file():
            raise FileNotFoundError(f"The {scripts_type}-install script was not found: {item}")
        dest_path = (script_base / name).resolve()
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest_path)


def download_wheel_deps(
    wheel_path: str | Path,
    dest: str | Path,
    only_binary: bool = True,
    extra_pip_args: list[str] | None = None) -> list[str]:
    """Resolve and download the wheel and all its dependencies into dest."""
    wheel_path = str(Path(wheel_path).resolve())
    dest = Path(dest).resolve()
    dest.mkdir(parents=True, exist_ok=True)
    before = set(Path(dest).glob("*.whl")) or []

    cmd = [
        sys.executable,
        "-m",
        "pip",
        "download",
        wheel_path,
        "--dest",
        str(dest)
    ]
    if only_binary:
        cmd += ["--only-binary", ":all:"]
    if extra_pip_args:
        cmd += list(extra_pip_args)

    result = subprocess.run(cmd, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"pip download failed:\n{result.stderr}")
    after = set(dest.glob("*.whl")) or []
    return sorted(f.name for f in set(after) - set(before)) or []


def get_wheel_metadata(wheel_path: str | Path,
                       *,
                       normalize_name: bool = True) -> tuple[str, str]:
    wheel_path = Path(wheel_path)
    if wheel_path.suffix != ".whl":
        raise ValueError(f"Not a wheel: {wheel_path}")
    with zipfile.ZipFile(wheel_path) as z:
        meta_filename = next(
            (n for n in z.namelist() if n.endswith(".dist-info/METADATA")),
            None)
        if not meta_filename:
            raise ValueError("METADATA file not found in wheel")
        meta_text = z.read(meta_filename).decode("utf-8", errors="replace")
    msg = Parser().parsestr(meta_text)
    name = msg.get("Name")
    version = msg.get("Version")
    if not name or not version:
        raise ValueError("Missing Name or Version in METADATA")
    if normalize_name:
        name = name.replace("_", "-").replace(" ", "-").lower()
    return name, version


def get_chub_name(package_name: str, version: str) -> str:
    return "-".join([package_name, version])


def create_chub_build_dir(wheel_path: str | Path,
                          chub_path: str | Path | None = None) -> Path:
    wheel_path = Path(wheel_path).resolve()
    if wheel_path.suffix != ".whl":
        raise ValueError(f"Not a wheel: {wheel_path}")
    chub_build_root = wheel_path.parent if chub_path is None else Path(chub_path).resolve().parent
    for dir_item in CHUB_BUILD_DIR_STRUCTURE:
        (chub_build_root / dir_item).mkdir(parents=True, exist_ok=True)
    chub_build_dir = Path(chub_build_root / CHUB_BUILD_DIR).resolve()
    Path(chub_build_dir / CHUBCONFIG_FILENAME).resolve().touch(exist_ok=True)
    return chub_build_dir


def verify_pip() -> None:
    """Ensure pip is available for the current Python.

    We verify `python -m pip --version` instead of relying on a `pip` script on
    PATH.
    """
    code = subprocess.call([sys.executable, "-m", "pip", "--version"])  # noqa: S603
    if code != 0:
        raise RuntimeError(
            "pip not found. Ensure 'python -m pip' works in this environment."
        )


def validate_files_exist(files: list[str] | [], context: str) -> None:
    for file in files:
        src = file.split("::", 1)[0]
        path = Path(src).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"{context} file not found: {src}")


def validate_chub_structure(chub_build_dir: Path,
                            post_install_scripts: list[Path] | [],
                            pre_install_scripts: list[Path] | [],
                            included_files: list[str] | []) -> None:
    # 1. Ensure the build dir exists and has a .chubconfig
    chubconfig_file = chub_build_dir / CHUBCONFIG_FILENAME
    if not chubconfig_file.exists():
        raise FileNotFoundError(f"Missing {CHUBCONFIG_FILENAME} in {chub_build_dir}")

    # 2. Confirm no leftover junk in libs/scripts
    libs = chub_build_dir / CHUB_LIBS_DIR
    if libs.exists() and any(p.is_file() for p in libs.iterdir()):
        raise FileExistsError(f"libs/ in {chub_build_dir} is not empty")
    scripts = chub_build_dir / CHUB_SCRIPTS_DIR
    if scripts.exists() and any(p.is_file() for p in scripts.iterdir()):
        raise FileExistsError(f"scripts/ in {chub_build_dir} is not empty")

    # 3. Validate included files
    if included_files:
        validate_files_exist(included_files, context="Include")

    # 4. Validate pre- and post-install scripts
    for script_tuple in [("post", post_install_scripts), ("pre", pre_install_scripts)]:
        script_type, scripts = script_tuple
        if scripts:
            for s in scripts:
                if not Path(s).expanduser().resolve().is_file():
                    raise FileNotFoundError(f"The {script_type}-install script was not found: {s}")


def build_chub(*,
               wheel_paths: list[Path],
               chub_path: str | Path | None = None,
               entrypoint: str | None = None,
               post_install_scripts: list[tuple[Path, str]] | [],
               pre_install_scripts: list[tuple[Path, str]] | [],
               included_files: list[str] | [],
               metadata: dict | None = None) -> Path:
    verify_pip()

    if not wheel_paths:
        raise ValueError("No wheels provided")

    metadata = metadata or {}
    main_wheel_name = str(metadata.get("main_wheel", Path(wheel_paths[0]).name))
    # Find the main wheel path by name; fall back to the first wheel path
    main_wheel_path = next((p for p in wheel_paths if p.name == main_wheel_name), wheel_paths[0])

    chub_build_dir = create_chub_build_dir(main_wheel_path, chub_path)

    package_name, version = get_wheel_metadata(main_wheel_path)
    chub_name = get_chub_name(package_name, version)

    validate_chub_structure(
        chub_build_dir,
        [path for path, _ in (post_install_scripts or [])],
        [path for path, _ in (pre_install_scripts or [])],
        included_files)

    wheel_libs_dir = chub_build_dir / CHUB_LIBS_DIR

    wheels_map: dict[str, list[str]] = {}
    for wp in wheel_paths:
        shutil.copy2(wp, wheel_libs_dir / wp.name)
        wheels_map[wp.name] = download_wheel_deps(wp, wheel_libs_dir)

    script_base = chub_build_dir / CHUB_SCRIPTS_DIR
    copy_install_scripts(script_base, post_install_scripts, CHUB_POST_INSTALL_SCRIPTS_DIR)
    copy_install_scripts(script_base, pre_install_scripts, CHUB_PRE_INSTALL_SCRIPTS_DIR)
    copy_included_files(chub_build_dir, included_files)
    copy_runtime_files(chub_build_dir)

    chubconfig_model = ChubConfig(
            name=package_name,
            version=version,
            entrypoint=entrypoint,
            wheels=wheels_map,
            includes=included_files or [],
            scripts=Scripts(
                pre=[name for _, name in (pre_install_scripts or [])],
                post=[name for _, name in (post_install_scripts or [])]),
            metadata=metadata or {})
    chubconfig_model.validate()
    chubconfig_file = Path(chub_build_dir / CHUBCONFIG_FILENAME).resolve()
    with chubconfig_file.open("w+", encoding="utf-8") as f:
        f.write(chubconfig_model.to_yaml())

    if chub_path is None:
        chub_path = chub_build_dir / f"{chub_name}.chub"

    output_path = create_chub_archive(chub_build_dir, Path(chub_path))
    print(f"Built {output_path}")
    return output_path
