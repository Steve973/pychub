import json
import sys
from unittest import mock

import pytest
import yaml

from pychub.model.chubconfig_model import ChubConfig
from pychub.model.chubproject_model import ChubProject
from pychub.model.scripts_model import Scripts


# ===== ChubConfig.from_mapping tests =====

def test_from_mapping_minimal():
    """Test creating ChubConfig with only required fields."""
    mapping = {
        "name": "test-package",
        "version": "1.0.0"
    }
    config = ChubConfig.from_mapping(mapping)

    assert config.name == "test-package"
    assert config.version == "1.0.0"
    assert config.entrypoint is None
    assert config.includes == []
    assert config.scripts.pre == []
    assert config.scripts.post == []
    assert config.pinned_wheels == []
    assert config.targets == []
    assert config.metadata == {}


def test_from_mapping_all_fields():
    """Test creating ChubConfig with all fields populated."""
    mapping = {
        "name": "full-package",
        "version": "2.5.3",
        "entrypoint": "module:function",
        "wheels": {
            "main.whl": ["dep1.whl", "dep2.whl"],
            "other.whl": []
        },
        "includes": ["file1.txt", "file2.py"],
        "scripts": {
            "pre": ["pre_script.sh"],
            "post": ["post_script.sh", "cleanup.sh"]
        },
        "pinned_wheels": [
            "main==1.2.3",
            "dep1==2.3.4",
            "dep2==3.4.5"
        ],
        "targets": ["target1", "target2"],
        "metadata": {"author": "Test Author", "description": "A test package"}
    }
    config = ChubConfig.from_mapping(mapping)

    assert config.name == "full-package"
    assert config.version == "2.5.3"
    assert config.entrypoint == "module:function"
    assert config.includes == ["file1.txt", "file2.py"]
    assert config.scripts.pre == ["pre_script.sh"]
    assert config.scripts.post == ["post_script.sh", "cleanup.sh"]
    assert config.pinned_wheels == ["main==1.2.3", "dep1==2.3.4", "dep2==3.4.5"]
    assert config.targets == ["target1", "target2"]
    assert config.metadata == {"author": "Test Author", "description": "A test package"}


def test_from_mapping_strips_whitespace():
    """Test that name and version are stripped of whitespace."""
    mapping = {
        "name": "  test-package  ",
        "version": "\t1.0.0\n"
    }
    config = ChubConfig.from_mapping(mapping)

    assert config.name == "test-package"
    assert config.version == "1.0.0"


def test_from_mapping_handles_none_values():
    """Test that None values are handled gracefully."""
    mapping = {
        "name": "test",
        "version": "1.0.0",
        "includes": None,
        "scripts": None,
        "pinned_wheels": None,
        "targets": None,
        "metadata": None
    }
    config = ChubConfig.from_mapping(mapping)

    assert config.includes == []
    assert config.scripts.pre == []
    assert config.scripts.post == []
    assert config.pinned_wheels == []
    assert config.targets == []
    assert config.metadata == {}


def test_from_mapping_converts_types():
    """Test that values are converted to appropriate types."""
    mapping = {
        "name": 123,  # Should be converted to string
        "version": 1.0,  # Should be converted to string
        "entrypoint": 456,  # Should be converted to string
        "includes": [111, 222],  # Should be converted to strings
        "pinned_wheels": ["789==1.2.3", "111==2.3.4", "222==3.4.5"],
        "targets": ["target1", "target2"]
    }
    config = ChubConfig.from_mapping(mapping)

    assert config.name == "123"
    assert config.version == "1.0"
    assert config.entrypoint == "456"
    assert config.pinned_wheels == ["789==1.2.3", "111==2.3.4", "222==3.4.5"]
    assert config.targets == ["target1", "target2"]
    assert config.includes == ["111", "222"]


def test_from_mapping_empty_dict():
    """Test creating ChubConfig from empty dict results in validation error."""
    with pytest.raises(ValueError, match="name is required"):
        ChubConfig.from_mapping({})


def test_from_mapping_missing_name():
    """Test that missing name raises validation error."""
    mapping = {"version": "1.0.0"}
    with pytest.raises(ValueError, match="name is required"):
        ChubConfig.from_mapping(mapping)


def test_from_mapping_missing_version():
    """Test that missing version raises validation error."""
    mapping = {"name": "test"}
    with pytest.raises(ValueError, match="version is required"):
        ChubConfig.from_mapping(mapping)


def test_from_mapping_empty_name():
    """Test that empty name raises validation error."""
    mapping = {"name": "", "version": "1.0.0"}
    with pytest.raises(ValueError, match="name is required"):
        ChubConfig.from_mapping(mapping)


def test_from_mapping_empty_version():
    """Test that empty version raises validation error."""
    mapping = {"name": "test", "version": ""}
    with pytest.raises(ValueError, match="version is required"):
        ChubConfig.from_mapping(mapping)


def test_from_yaml_unicode():
    """Test parsing YAML with unicode characters."""
    yaml_str = """
name: naïve-β
version: 1.0.0
metadata:
  description: 数据处理
"""
    config = ChubConfig.from_yaml(yaml_str)

    assert config.name == "naïve-β"
    assert config.metadata["description"] == "数据处理"


def test_from_yaml_raises_when_yaml_not_available():
    """Test that from_yaml raises RuntimeError when PyYAML is not installed."""
    with mock.patch('pychub.model.chubconfig_model.yaml', None):
        with pytest.raises(RuntimeError, match="PyYAML not installed"):
            ChubConfig.from_yaml("name: test\nversion: 1.0.0")


def test_to_yaml_raises_when_yaml_not_available():
    """Test that to_yaml raises RuntimeError when PyYAML is not installed."""
    config = ChubConfig(name="test", version="1.0.0")
    with mock.patch('pychub.model.chubconfig_model.yaml', None):
        with pytest.raises(RuntimeError, match="PyYAML not installed"):
            config.to_yaml()


# ===== ChubConfig.from_yaml tests =====

def test_from_yaml_minimal():
    """Test parsing minimal YAML config."""
    yaml_str = """
name: test-package
version: 1.0.0
"""
    config = ChubConfig.from_yaml(yaml_str)

    assert config.name == "test-package"
    assert config.version == "1.0.0"


def test_from_yaml_full():
    """Test parsing complete YAML config."""
    yaml_str = """
name: full-package
version: 2.5.3
entrypoint: module:function
includes:
  - file1.txt
  - file2.py
scripts:
  pre:
    - pre_script.sh
  post:
    - post_script.sh
pinned_wheels:
  - main==1.2.3
  - dep1==2.3.4
  - dep2==3.4.5
targets:
  - target1
  - target2
metadata:
  author: Test Author
"""
    config = ChubConfig.from_yaml(yaml_str)

    assert config.name == "full-package"
    assert config.version == "2.5.3"
    assert config.entrypoint == "module:function"
    assert config.includes == ["file1.txt", "file2.py"]
    assert config.scripts.pre == ["pre_script.sh"]
    assert config.scripts.post == ["post_script.sh"]
    assert config.pinned_wheels == ["main==1.2.3", "dep1==2.3.4", "dep2==3.4.5"]
    assert config.targets == ["target1", "target2"]
    assert config.metadata == {"author": "Test Author"}


def test_from_yaml_empty_string():
    """Test parsing empty YAML string."""
    with pytest.raises(ValueError, match="name is required"):
        ChubConfig.from_yaml("")


def test_from_yaml_only_whitespace():
    """Test parsing YAML with only whitespace."""
    with pytest.raises(ValueError, match="name is required"):
        ChubConfig.from_yaml("   \n\n  ")


# ===== ChubConfig.from_file tests =====

def test_from_file_minimal(tmp_path):
    """Test loading minimal config from file."""
    config_file = tmp_path / "test.chubconfig"
    config_file.write_text("""
name: file-package
version: 3.2.1
""", encoding="utf-8")

    config = ChubConfig.from_file(config_file)

    assert config.name == "file-package"
    assert config.version == "3.2.1"


def test_from_file_full(tmp_path):
    """Test loading full config from file."""
    config_file = tmp_path / "full.chubconfig"
    config_file.write_text("""
name: full-file-package
version: 1.0.0
entrypoint: app:main
wheels:
  app.whl:
    - requests.whl
includes:
  - README.md
scripts:
  pre:
    - setup.sh
  post:
    - cleanup.sh
pinned_wheels:
  - main==1.2.3
  - dep1==2.3.4
  - dep2==3.4.5
targets:
  - target1
  - target2
metadata:
  license: MIT
""", encoding="utf-8")

    config = ChubConfig.from_file(config_file)

    assert config.name == "full-file-package"
    assert config.version == "1.0.0"
    assert config.entrypoint == "app:main"
    assert config.includes == ["README.md"]
    assert config.scripts.pre == ["setup.sh"]
    assert config.scripts.post == ["cleanup.sh"]
    assert config.pinned_wheels == ["main==1.2.3", "dep1==2.3.4", "dep2==3.4.5"]
    assert config.targets == ["target1", "target2"]
    assert config.metadata == {"license": "MIT"}


def test_from_file_path_as_string(tmp_path):
    """Test loading config using string path."""
    config_file = tmp_path / "test.chubconfig"
    config_file.write_text("""
name: string-path
version: 1.0.0
""", encoding="utf-8")

    config = ChubConfig.from_file(str(config_file))

    assert config.name == "string-path"
    assert config.version == "1.0.0"


def test_from_file_unicode(tmp_path):
    """Test loading config with unicode from file."""
    config_file = tmp_path / "unicode.chubconfig"
    config_file.write_text("""
name: naïve-β
version: 1.0.0
metadata:
  description: 数据处理工具
""", encoding="utf-8")

    config = ChubConfig.from_file(config_file)

    assert config.name == "naïve-β"
    assert config.metadata["description"] == "数据处理工具"


def test_from_file_nonexistent(tmp_path):
    """Test loading from nonexistent file raises error."""
    config_file = tmp_path / "nonexistent.chubconfig"

    with pytest.raises(FileNotFoundError):
        ChubConfig.from_file(config_file)


# ===== ChubConfig.to_mapping tests =====

def test_to_mapping_minimal():
    """Test converting minimal config to mapping."""
    config = ChubConfig(name="test", version="1.0.0")
    mapping = config.to_mapping()

    assert mapping["name"] == "test"
    assert mapping["version"] == "1.0.0"
    assert mapping["entrypoint"] is None
    assert mapping["includes"] == []
    assert mapping["scripts"] == {"pre": [], "post": []}
    assert mapping["pinned_wheels"] == []
    assert mapping["targets"] == []
    assert mapping["metadata"] == {}


def test_to_mapping_full():
    """Test converting full config to mapping."""
    config = ChubConfig(
        name="full",
        version="2.0.0",
        entrypoint="mod:func",
        includes=["file.txt"],
        scripts=Scripts(pre=["pre.sh"], post=["post.sh"]),
        pinned_wheels=["a==1.2.3", "b==3.4.5"],
        targets=["target1", "target2"],
        metadata={"key": "value"}
    )
    mapping = config.to_mapping()

    assert mapping["name"] == "full"
    assert mapping["version"] == "2.0.0"
    assert mapping["entrypoint"] == "mod:func"
    assert mapping["includes"] == ["file.txt"]
    assert mapping["scripts"] == {"pre": ["pre.sh"], "post": ["post.sh"]}
    assert mapping["pinned_wheels"] == ["a==1.2.3", "b==3.4.5"]
    assert mapping["targets"] == ["target1", "target2"]
    assert mapping["metadata"] == {"key": "value"}


def test_to_mapping_creates_copies():
    """Test that to_mapping creates copies of mutable fields."""
    scripts = Scripts(pre=["pre.sh"])
    config = ChubConfig(
        name="test",
        version="1.0.0",
        includes=["file.txt"],
        scripts=scripts,
        pinned_wheels=["a==1.2.3", "b==2.3.4"],
        targets=["target1", "target2"],
        metadata={"meta": "data"}
    )

    mapping = config.to_mapping()

    # Modify the mapping
    mapping["includes"].append("other.txt")
    mapping["scripts"]["pre"].append("other.sh")
    mapping["pinned_wheels"].append("c==3.4.5")
    mapping["targets"].append("target3")
    mapping["metadata"]["meta2"] = "data2"

    # Original config should be unchanged (frozen dataclass)
    assert config.includes == ["file.txt"]
    assert config.scripts.pre == ["pre.sh"]
    assert config.pinned_wheels == ["a==1.2.3", "b==2.3.4"]
    assert config.targets == ["target1", "target2"]
    assert config.metadata == {"meta": "data"}


# ===== ChubConfig.to_json tests =====

def test_to_json_minimal():
    """Test converting minimal config to JSON."""
    config = ChubConfig(name="test", version="1.0.0")
    json_str = config.to_json()

    parsed = json.loads(json_str)
    assert parsed["name"] == "test"
    assert parsed["version"] == "1.0.0"


def test_to_json_full():
    """Test converting full config to JSON."""
    config = ChubConfig(
        name="full",
        version="2.0.0",
        entrypoint="mod:func",
        includes=["file.txt"],
        scripts=Scripts(pre=["pre.sh"], post=["post.sh"]),
        pinned_wheels=["a==1.2.3", "b==3.4.5"],
        targets=["target1", "target2"],
        metadata={"key": "value"}
    )
    json_str = config.to_json()

    parsed = json.loads(json_str)
    assert parsed["name"] == "full"
    assert parsed["version"] == "2.0.0"
    assert parsed["entrypoint"] == "mod:func"
    assert parsed["includes"] == ["file.txt"]
    assert parsed["scripts"] == {"pre": ["pre.sh"], "post": ["post.sh"]}
    assert parsed["pinned_wheels"] == ["a==1.2.3", "b==3.4.5"]
    assert parsed["targets"] == ["target1", "target2"]
    assert parsed["metadata"] == {"key": "value"}


def test_to_json_custom_indent():
    """Test JSON output with custom indent."""
    config = ChubConfig(name="test", version="1.0.0")

    json_default = config.to_json()
    json_no_indent = config.to_json(indent=None)
    json_large_indent = config.to_json(indent=4)

    # All should parse to same object
    assert json.loads(json_default) == json.loads(json_no_indent) == json.loads(json_large_indent)

    # But formatting should differ
    assert len(json_no_indent) < len(json_default) < len(json_large_indent)


def test_to_json_unicode():
    """Test JSON output with unicode characters."""
    config = ChubConfig(
        name="naïve-β",
        version="1.0.0",
        metadata={"description": "数据处理"}
    )
    json_str = config.to_json()

    parsed = json.loads(json_str)
    assert parsed["name"] == "naïve-β"
    assert parsed["metadata"]["description"] == "数据处理"

    # Ensure unicode is preserved (not escaped)
    assert "naïve-β" in json_str
    assert "数据处理" in json_str


# ===== ChubConfig.to_yaml tests =====

def test_to_yaml_minimal():
    """Test converting minimal config to YAML."""
    config = ChubConfig(name="test", version="1.0.0")
    yaml_str = config.to_yaml()

    parsed = yaml.safe_load(yaml_str)
    assert parsed["name"] == "test"
    assert parsed["version"] == "1.0.0"


def test_to_yaml_full():
    """Test converting full config to YAML."""
    config = ChubConfig(
        name="full",
        version="2.0.0",
        entrypoint="mod:func",
        includes=["file.txt"],
        scripts=Scripts(pre=["pre.sh"], post=["post.sh"]),
        pinned_wheels=["a==1.2.3", "b==3.4.5"],
        targets=["target1", "target2"],
        metadata={"key": "value"}
    )
    yaml_str = config.to_yaml()

    parsed = yaml.safe_load(yaml_str)
    assert parsed["name"] == "full"
    assert parsed["version"] == "2.0.0"
    assert parsed["entrypoint"] == "mod:func"
    assert parsed["includes"] == ["file.txt"]
    assert parsed["scripts"] == {"pre": ["pre.sh"], "post": ["post.sh"]}
    assert parsed["pinned_wheels"] == ["a==1.2.3", "b==3.4.5"]
    assert parsed["targets"] == ["target1", "target2"]
    assert parsed["metadata"] == {"key": "value"}


def test_to_yaml_unicode():
    """Test YAML output with unicode characters."""
    config = ChubConfig(
        name="naïve-β",
        version="1.0.0",
        metadata={"description": "数据处理"}
    )
    yaml_str = config.to_yaml()

    parsed = yaml.safe_load(yaml_str)
    assert parsed["name"] == "naïve-β"
    assert parsed["metadata"]["description"] == "数据处理"

    # Ensure unicode is preserved
    assert "naïve-β" in yaml_str
    assert "数据处理" in yaml_str


def test_to_yaml_key_order():
    """Test that YAML maintains field order (not sorted)."""
    config = ChubConfig(
        name="test",
        version="1.0.0",
        metadata={"zebra": "last", "apple": "first"}
    )
    yaml_str = config.to_yaml()

    # Check that 'name' comes before 'version' in output
    name_pos = yaml_str.index("name:")
    version_pos = yaml_str.index("version:")
    assert name_pos < version_pos


# ===== ChubConfig.validate tests =====

def test_validate_success_minimal():
    """Test validation passes with minimal valid config."""
    config = ChubConfig(name="test", version="1.0.0")
    config.validate()  # Should not raise


def test_validate_success_full():
    """Test validation passes with full valid config."""
    config = ChubConfig(
        name="full",
        version="2.0.0",
        entrypoint="module:function",
        includes=["file.txt"],
        scripts=Scripts(pre=["pre.sh"], post=["post.sh"]),
        pinned_wheels=["main==1.2.3", "dep==3.4.5", "other==5.6.7"],
        targets=["target1", "target2"],
        metadata={"key": "value"}
    )
    config.validate()  # Should not raise


def test_validate_fails_empty_name():
    """Test validation fails with empty name."""
    config = ChubConfig(name="", version="1.0.0")
    with pytest.raises(ValueError, match="name is required"):
        config.validate()


def test_validate_fails_empty_version():
    """Test validation fails with empty version."""
    config = ChubConfig(name="test", version="")
    with pytest.raises(ValueError, match="version is required"):
        config.validate()


def test_validate_fails_entrypoint_with_space():
    """Test validation fails when entrypoint contains space."""
    config = ChubConfig(
        name="test",
        version="1.0.0",
        entrypoint="module:function --arg"
    )
    with pytest.raises(ValueError, match="entrypoint must be a single token"):
        config.validate()


def test_validate_allows_entrypoint_with_colon():
    """Test validation allows entrypoint with colon."""
    config = ChubConfig(
        name="test",
        version="1.0.0",
        entrypoint="module:function"
    )
    config.validate()  # Should not raise


def test_validate_allows_none_entrypoint():
    """Test validation allows None entrypoint."""
    config = ChubConfig(
        name="test",
        version="1.0.0",
        entrypoint=None
    )
    config.validate()  # Should not raise


def test_validate_allows_empty_wheels():
    """Test validation allows empty wheels dict."""
    config = ChubConfig(
        name="test",
        version="1.0.0",
        pinned_wheels=[]
    )
    config.validate()  # Should not raise


def test_validate_multiple_wheel_errors():
    """Test validation reports first wheel error."""
    config = ChubConfig(
        name="test",
        version="1.0.0",
        pinned_wheels = ["a=1.2.3", "b>=3.4.5"],
        targets = ["target1", "target2"],
    )
    with pytest.raises(ValueError, match="pinned wheel must be in the format 'name==ver': a=1.2.3"):
        config.validate()


# ===== Round-trip tests =====

def test_roundtrip_mapping():
    """Test that config survives mapping round-trip."""
    original = ChubConfig(
        name="roundtrip",
        version="1.0.0",
        entrypoint="app:main",
        includes=["file.txt"],
        scripts=Scripts(pre=["pre.sh"], post=["post.sh"]),
        pinned_wheels=["a==1.2.3", "b==3.4.5"],
        targets=["target1", "target2"],
        metadata={"key": "value"}
    )

    mapping = original.to_mapping()
    restored = ChubConfig.from_mapping(mapping)

    assert restored.name == original.name
    assert restored.version == original.version
    assert restored.entrypoint == original.entrypoint
    assert restored.includes == original.includes
    assert restored.scripts.pre == original.scripts.pre
    assert restored.scripts.post == original.scripts.post
    assert restored.pinned_wheels == original.pinned_wheels
    assert restored.targets == original.targets
    assert restored.metadata == original.metadata


def test_roundtrip_yaml():
    """Test that config survives YAML round-trip."""
    original = ChubConfig(
        name="roundtrip",
        version="1.0.0",
        entrypoint="app:main",
        includes=["file.txt"],
        scripts=Scripts(pre=["pre.sh"], post=["post.sh"]),
        pinned_wheels=["a==1.2.3", "b==3.4.5"],
        targets=["target1", "target2"],
        metadata={"key": "value"}
    )

    yaml_str = original.to_yaml()
    restored = ChubConfig.from_yaml(yaml_str)

    assert restored.name == original.name
    assert restored.version == original.version
    assert restored.entrypoint == original.entrypoint
    assert restored.includes == original.includes
    assert restored.scripts.pre == original.scripts.pre
    assert restored.scripts.post == original.scripts.post
    assert restored.pinned_wheels == original.pinned_wheels
    assert restored.targets == original.targets
    assert restored.metadata == original.metadata


def test_roundtrip_file(tmp_path):
    """Test that config survives file round-trip."""
    original = ChubConfig(
        name="roundtrip",
        version="1.0.0",
        entrypoint="app:main",
        includes=["file.txt"],
        scripts=Scripts(pre=["pre.sh"], post=["post.sh"]),
        pinned_wheels=["a==1.2.3", "b==3.4.5"],
        targets=["target1", "target2"],
        metadata={"key": "value"}
    )

    config_file = tmp_path / "test.chubconfig"
    config_file.write_text(original.to_yaml(), encoding="utf-8")
    restored = ChubConfig.from_file(config_file)

    assert restored.name == original.name
    assert restored.version == original.version
    assert restored.entrypoint == original.entrypoint
    assert restored.includes == original.includes
    assert restored.scripts.pre == original.scripts.pre
    assert restored.scripts.post == original.scripts.post
    assert restored.pinned_wheels == original.pinned_wheels
    assert restored.targets == original.targets
    assert restored.metadata == original.metadata


def test_roundtrip_unicode(tmp_path):
    """Test that unicode survives round-trips."""
    original = ChubConfig(
        name="naïve-β",
        version="1.0.0",
        metadata={"description": "数据处理工具"}
    )

    # YAML round-trip
    yaml_str = original.to_yaml()
    from_yaml = ChubConfig.from_yaml(yaml_str)
    assert from_yaml.name == "naïve-β"
    assert from_yaml.metadata["description"] == "数据处理工具"

    # JSON round-trip
    json_str = original.to_json()
    mapping = json.loads(json_str)
    from_json = ChubConfig.from_mapping(mapping)
    assert from_json.name == "naïve-β"
    assert from_json.metadata["description"] == "数据处理工具"

    # File round-trip
    config_file = tmp_path / "unicode.chubconfig"
    config_file.write_text(original.to_yaml(), encoding="utf-8")
    from_file = ChubConfig.from_file(config_file)
    assert from_file.name == "naïve-β"
    assert from_file.metadata["description"] == "数据处理工具"


# ===== Frozen/immutability tests =====

def test_config_is_frozen():
    """Test that ChubConfig instances are frozen (immutable)."""
    config = ChubConfig(name="test", version="1.0.0")

    with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
        config.name = "changed"


def test_chubproject_has_slots():
    """Validate that ChubProject uses slots when supported."""
    config = ChubProject()
    cls = type(config)

    if sys.version_info >= (3, 10):
        # Python 3.10+ truly supports dataclass(slots=True)
        assert hasattr(cls, "__slots__"), "Expected __slots__ on 3.10+"
        assert not hasattr(config, "__dict__"), "Expected __dict__ to be removed on 3.10+"
    else:
        # 3.9 shim: slots arg is stripped; class should *not* have __slots__
        assert not hasattr(cls, "__slots__"), "__slots__ should not exist under shimmed 3.9"
        assert hasattr(config, "__dict__"), "Shimmed 3.9 should still have __dict__"
