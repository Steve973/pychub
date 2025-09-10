import pytest


@pytest.fixture(autouse=True)
def fake_dist_wheels(monkeypatch, tmp_path):
    # Make two fake wheel paths
    dist = tmp_path / "dist"
    dist.mkdir()
    files = [
        dist / "pychub-0.0.0-py3-none-any.whl",
        dist / "extra-0.0.0-py3-none-any.whl",
    ]
    for p in files:
        p.touch()

    # Only patch the chubproject_model module's use of glob
    def _fake_glob(pattern: str):
        # your code uses glob.glob(os.path.join(cwd, "dist", "*.whl"))
        if pattern.endswith("dist/*.whl"):
            return [str(p) for p in sorted(files)]
        return []

    monkeypatch.setattr(
        "pychub.model.chubproject_model.glob.glob",
        _fake_glob,
        raising=True,
    )