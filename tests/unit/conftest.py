import pytest


@pytest.fixture
def fake_dist_wheels(monkeypatch, tmp_path):
    # Make two fake wheel paths
    dist = tmp_path / "dist"
    dist.mkdir()
    files = [
        dist / "extra-0.0.0-py3-none-any.whl",
        dist / "pychub-1.0.0-py3-none-any.whl",
        dist / "pkg-1.0.0-py3-none-any.whl",
    ]
    for f in files:
        f.touch()

    # Only patch the chubproject_model module's use of glob
    def _fake_glob(pattern: str):
        # your code uses glob.glob(os.path.join(cwd, "dist", "*.whl"))
        if pattern.endswith("dist/*.whl"):
            return [str(p) for p in sorted(files)]
        return []

    monkeypatch.setattr(
        "pychub.model.chubproject_model.glob.glob",
        _fake_glob,
        raising=True)