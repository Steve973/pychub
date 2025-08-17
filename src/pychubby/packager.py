import shutil
import subprocess
import sys

import yaml
import zipfile
from email.parser import Parser
from pathlib import Path

from .constants import CHUB_BUILD_DIR, CHUB_LIBS_DIR, CHUB_SCRIPTS_DIR, CHUBCONFIG_FILENAME, RUNTIME_DIR


def create_chub_archive(chub_build_dir: Path, chub_archive_path: Path) -> Path:
    with zipfile.ZipFile(chub_archive_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_path in chub_build_dir.rglob("*"):
            arcname = file_path.relative_to(chub_build_dir)
            zf.write(file_path, arcname)
    return chub_archive_path


def copy_runtime_files(chub_build_dir: Path) -> None:
    runtime_src = Path(__file__).parent / RUNTIME_DIR
    runtime_dst = chub_build_dir / RUNTIME_DIR
    shutil.copytree(runtime_src, runtime_dst)
    chub_main_py = chub_build_dir / "__main__.py"
    chub_main_py.write_text(
        f"import runpy; runpy.run_module('{RUNTIME_DIR}', run_name='__main__')\n")


def copy_included_files(wheel_package_dir: Path,
                        included_files: list[str] = None) -> None:
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

        if dest_str:
            dest_path = (wheel_package_dir / dest_str).resolve()
        else:
            dest_path = (wheel_package_dir / src.name).resolve()

        # Optional: prevent directory traversal (security hardening)
        if not str(dest_path).startswith(str(wheel_package_dir)):
            raise ValueError(f"Destination '{dest_path}' escapes wheel package directory")

        dest_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dest_path)


def copy_post_install_scripts(wheel_package_dir: Path,
                              post_install_scripts: list[str] = None) -> None:
    if not post_install_scripts:
        return

    for item in post_install_scripts:
        src = Path(item).expanduser().resolve()
        if not src.is_file():
            raise FileNotFoundError(f"Post-install script not found: {item}")
        dest_path = (wheel_package_dir / CHUB_SCRIPTS_DIR / Path(item).name).resolve()
        shutil.copy2(src, dest_path)


def create_chubconfig(package_name: str,
                     version: str,
                     entrypoint: str,
                     post_install_scripts: list[str] = None,
                     included_files: list[str] = None,
                     metadata: dict = None) -> str:
    """
    Create a .chubconfig YAML document that looks like this:
    ---
    name: requests
    version: 2.31.0
    entrypoint: requests.cli:main
    post_install_scripts:
      - install_cert.sh
    includes:
      - extra.cfg
      - config.json::conf
    metadata:
      tags: [http, client]
      maintainer: someone@example.com

    It has a document start marker line, and a newline at the end.
    """

    chubconfig = {
        "name": package_name,
        "version": version,
        "entrypoint": entrypoint,
        "post_install_scripts": post_install_scripts or [],
        "includes": included_files or [],
        "metadata": metadata or {}
    }
    return yaml.safe_dump(chubconfig, sort_keys=False, allow_unicode=True, explicit_start=True) + "\n\n"


def download_wheel_deps(wheel_path: str | Path,
                        dest: str | Path,
                        only_binary: bool = True,
                        extra_pip_args: list[str] | None = None) -> None:
    """
    Resolve and download the wheel and all its dependencies into dest
    without installing them.
    """
    wheel_path = str(Path(wheel_path).resolve())
    dest = Path(dest).resolve()
    dest.mkdir(parents=True, exist_ok=True)

    cmd = [sys.executable, "-m", "pip", "download", wheel_path, "--dest", str(dest)]
    if only_binary:
        cmd += ["--only-binary", ":all:"]
    if extra_pip_args:
        cmd += extra_pip_args

    result = subprocess.run(cmd, text=True, capture_output=True)
    if result.returncode != 0:
        raise RuntimeError(f"pip download failed:\n{result.stderr}")


def get_wheel_metadata(wheel_path: str | Path, normalize_name: bool = True) -> tuple[str, str]:
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


def get_wheel_package_dir(package_name: str,
                          version: str,
                          chub_build_dir: str | Path) -> Path:
    wheel_package_name = "-".join([package_name, version])
    wheel_package_dir = Path(chub_build_dir / wheel_package_name).resolve()
    wheel_package_dir.mkdir(parents=True, exist_ok=True)
    wheel_libs_dir = wheel_package_dir / CHUB_LIBS_DIR
    wheel_scripts_dir = wheel_package_dir / CHUB_SCRIPTS_DIR
    wheel_libs_dir.mkdir(parents=True, exist_ok=True)
    wheel_scripts_dir.mkdir(parents=True, exist_ok=True)
    return wheel_package_dir


def get_chub_build_dir(wheel_path: str | Path,
                       chub_path: str | Path = None) -> Path:
    if wheel_path.suffix != ".whl":
        raise ValueError(f"Not a wheel: {wheel_path}")
    wheel_path = Path(wheel_path).resolve()
    if chub_path is not None:
        chub_path = Path(chub_path).resolve()
        chub_build_root = chub_path.parent / CHUB_BUILD_DIR
    else:
        chub_build_root = wheel_path.parent / CHUB_BUILD_DIR
    chub_build_root = Path(chub_build_root).resolve()
    return chub_build_root


def create_chub_build_dir_structure(wheel_path: str | Path,
                                    chub_path: str | Path = None) -> Path:
    chub_build_dir = get_chub_build_dir(wheel_path, chub_path)
    chub_build_dir.mkdir(parents=True, exist_ok=True)
    chubconfig_file = Path(chub_build_dir / CHUBCONFIG_FILENAME).resolve()
    chubconfig_file.touch(exist_ok=True)
    return chub_build_dir


def verify_pip():
    if shutil.which("pip") is None:
        raise RuntimeError("pip not found. Make sure pip is available in your Python environment.")


def validate_files_exist(files: list[str], context: str) -> None:
    for file in files:
        # If includes use 'src::dest' format, extract src part
        src = file.split("::", 1)[0]
        path = Path(src).expanduser().resolve()
        if not path.is_file():
            raise FileNotFoundError(f"{context} file not found: {src}")


def validate_chub_structure(wheel_package_dir: Path,
                            entrypoint: str = None,
                            post_install_scripts: list[str] = None,
                            included_files: list[str] = None) -> None:
    chub_build_dir = wheel_package_dir.parent

    # 1. Prevent overwriting existing wheel package
    if wheel_package_dir.exists() and wheel_package_dir.is_dir():
        raise FileExistsError(
            f"Wheel package directory '{wheel_package_dir}' already exists. "
            "Each wheel must be added exactly once.")

    # 2. Ensure the build dir exists and has a .chubconfig
    chubconfig_file = chub_build_dir / CHUBCONFIG_FILENAME
    if not chubconfig_file.exists():
        raise FileNotFoundError(f"Missing {CHUBCONFIG_FILENAME} in build directory")

    # 3. Check for name-version collision in existing .chubconfig
    try:
        with open(chubconfig_file, "r", encoding="utf-8") as f:
            docs = list(yaml.safe_load_all(f))
    except yaml.YAMLError as e:
        raise ValueError(f"Failed to parse {CHUBCONFIG_FILENAME}: {e}")

    parts = wheel_package_dir.name.split("-", 1)
    if len(parts) != 2:
        raise ValueError(
            f"Wheel package directory name must be in the format 'name-version', "
            f"got '{wheel_package_dir.name}'")
    new_name, new_version = parts

    for doc in docs:
        if not doc:
            continue
        existing_name = doc.get("name")
        existing_version = doc.get("version")
        if existing_name == new_name and existing_version == new_version:
            raise ValueError(
                f"A wheel with name '{new_name}' and version '{new_version}' is already defined "
                f"in {CHUBCONFIG_FILENAME}"
            )

    # 4. Check reserved top-level names
    reserved = {"runtime", "__main__.py", CHUBCONFIG_FILENAME}
    if new_name in reserved:
        raise ValueError(
            f"'{wheel_package_dir.name}' is a reserved name and cannot be used for a wheel package"
        )

    # 5. Confirm no leftover junk in libs/scripts
    libs = wheel_package_dir / CHUB_LIBS_DIR
    scripts = wheel_package_dir / CHUB_SCRIPTS_DIR
    if libs.exists() and any(libs.iterdir()):
        raise FileExistsError(f"libs/ directory in {wheel_package_dir} is not empty")
    if scripts.exists() and any(scripts.iterdir()):
        raise FileExistsError(f"scripts/ directory in {wheel_package_dir} is not empty")

    # 6. Validate included files
    if included_files:
        validate_files_exist(included_files, context="Include")

    # 7. Validate post-install scripts
    if post_install_scripts:
        validate_files_exist(post_install_scripts, context="Post-install script")

    # 8. Validate entrypoint
    if entrypoint:
        entrypoint_parts = entrypoint.split(":", 1)
        if len(entrypoint_parts) != 2:
            raise ValueError(f"Invalid entrypoint format. Expected 'module:function', got '{entrypoint}'")


def build_chub(wheel_path: str | Path,
               chub_path: str | Path = None,
               entrypoint: str = None,
               post_install_scripts: list[str] = None,
               included_files: list[str] = None,
               metadata: dict = None) -> Path:
    verify_pip()
    chub_build_dir = create_chub_build_dir_structure(wheel_path, chub_path)
    package_name, version = get_wheel_metadata(wheel_path)
    wheel_package_dir = get_wheel_package_dir(package_name, version, chub_build_dir)
    validate_chub_structure(wheel_package_dir, post_install_scripts, included_files)
    wheel_libs_dir = wheel_package_dir / CHUB_LIBS_DIR
    shutil.copy2(wheel_path, wheel_libs_dir / wheel_path.name)
    download_wheel_deps(wheel_path, wheel_libs_dir)
    copy_post_install_scripts(wheel_package_dir, post_install_scripts)
    copy_included_files(wheel_package_dir, included_files)
    copy_runtime_files(chub_build_dir)
    chubconfig_text = create_chubconfig(
        package_name=package_name,
        version=version,
        entrypoint=entrypoint,
        post_install_scripts=post_install_scripts,
        included_files=included_files,
        metadata=metadata)
    chubconfig_file = Path(chub_build_dir / CHUBCONFIG_FILENAME).resolve()
    with chubconfig_file.open("a", encoding="utf-8") as f:
        f.write(chubconfig_text)
    if chub_path is None:
        chub_path = chub_build_dir / wheel_package_dir.name
    output_path = create_chub_archive(chub_build_dir, chub_path)
    print(f"Built {output_path}")
    return output_path
