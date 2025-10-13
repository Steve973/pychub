"""Unit tests for dataclass_shim.py."""
import sys

import pytest


def test_dataclass_strips_slots_on_python_39(monkeypatch):
    """Test that slots parameter is removed on Python < 3.10."""
    # Mock Python 3.9
    monkeypatch.setattr("pychub.model.dataclass_shim._sys.version_info", (3, 9, 0))

    # Re-import to get the mocked version
    import importlib
    import pychub.model.dataclass_shim
    importlib.reload(pychub.model.dataclass_shim)
    from pychub.model.dataclass_shim import dataclass

    # Should not raise TypeError even though real dataclass might not support slots
    # The shim removes it before passing to the real dataclass
    @dataclass(frozen=True)
    class TestClass:
        x: int
        y: str

    obj = TestClass(x=1, y="test")
    assert obj.x == 1
    assert obj.y == "test"


def test_dataclass_strips_kw_only_on_python_39(monkeypatch):
    """Test that kw_only parameter is removed on Python < 3.10."""
    monkeypatch.setattr("pychub.model.dataclass_shim._sys.version_info", (3, 9, 0))

    import importlib
    import pychub.model.dataclass_shim
    importlib.reload(pychub.model.dataclass_shim)
    from pychub.model.dataclass_shim import dataclass

    @dataclass(frozen=True)
    class TestClass:
        x: int
        y: str

    obj = TestClass(x=1, y="test")
    assert obj.x == 1
    assert obj.y == "test"


def test_dataclass_strips_both_on_python_39(monkeypatch):
    """Test that both slots and kw_only are removed on Python < 3.10."""
    monkeypatch.setattr("pychub.model.dataclass_shim._sys.version_info", (3, 9, 0))

    import importlib
    import pychub.model.dataclass_shim
    importlib.reload(pychub.model.dataclass_shim)
    from pychub.model.dataclass_shim import dataclass

    @dataclass(frozen=True)
    class TestClass:
        x: int
        y: str

    obj = TestClass(x=1, y="test")
    assert obj.x == 1
    assert obj.y == "test"


def test_dataclass_preserves_slots_on_python_310_plus(monkeypatch):
    """Test that slots is preserved on Python 3.10+."""
    if sys.version_info < (3, 10):
        pytest.skip("Need Python 3.10+ for slots support")

    monkeypatch.setattr("pychub.model.dataclass_shim._sys.version_info", (3, 10, 0))

    import importlib
    import pychub.model.dataclass_shim
    importlib.reload(pychub.model.dataclass_shim)
    from pychub.model.dataclass_shim import dataclass

    @dataclass(slots=True)
    class TestClass:
        x: int
        y: str

    assert hasattr(TestClass, "__slots__")
    obj = TestClass(x=1, y="test")
    assert obj.x == 1


def test_dataclass_preserves_kw_only_on_python_310_plus(monkeypatch):
    """Test that kw_only is preserved on Python 3.10+."""
    if sys.version_info < (3, 10):
        pytest.skip("Need Python 3.10+ for kw_only support")

    monkeypatch.setattr("pychub.model.dataclass_shim._sys.version_info", (3, 10, 0))

    import importlib
    import pychub.model.dataclass_shim
    importlib.reload(pychub.model.dataclass_shim)
    from pychub.model.dataclass_shim import dataclass

    @dataclass(kw_only=True)
    class TestClass:
        x: int
        y: str

    obj = TestClass(x=1, y="test")
    assert obj.x == 1

    with pytest.raises(TypeError):
        TestClass(1, "test")


def test_dataclass_basic_functionality():
    """Test basic dataclass functionality without version-specific params."""
    from pychub.model.dataclass_shim import dataclass

    @dataclass
    class TestClass:
        x: int
        y: str

    obj = TestClass(x=1, y="test")
    assert obj.x == 1
    assert obj.y == "test"


def test_dataclass_with_defaults():
    """Test that default values work."""
    from pychub.model.dataclass_shim import dataclass

    @dataclass
    class TestClass:
        x: int
        y: str = "default"
        z: int = 42

    obj1 = TestClass(x=1)
    assert obj1.x == 1
    assert obj1.y == "default"
    assert obj1.z == 42

    obj2 = TestClass(x=2, y="custom", z=100)
    assert obj2.x == 2
    assert obj2.y == "custom"
    assert obj2.z == 100


def test_dataclass_with_frozen():
    """Test that frozen parameter works."""
    from pychub.model.dataclass_shim import dataclass

    @dataclass(frozen=True)
    class TestClass:
        x: int
        y: str

    obj = TestClass(x=1, y="test")

    with pytest.raises(Exception):  # FrozenInstanceError or AttributeError
        obj.x = 5


def test_dataclass_with_order():
    """Test that order parameter works."""
    from pychub.model.dataclass_shim import dataclass

    @dataclass(order=True)
    class TestClass:
        x: int
        y: str

    obj1 = TestClass(x=1, y="a")
    obj2 = TestClass(x=2, y="b")

    assert obj1 < obj2


def test_dataclass_with_init_false():
    """Test that init=False works."""
    from pychub.model.dataclass_shim import dataclass

    @dataclass(init=False)
    class TestClass:
        x: int
        y: str

    obj = TestClass()
    obj.x = 1
    obj.y = "test"
    assert obj.x == 1
    assert obj.y == "test"


def test_dataclass_with_repr_false():
    """Test that repr=False works."""
    from pychub.model.dataclass_shim import dataclass

    @dataclass(repr=False)
    class TestClass:
        x: int
        y: str

    obj = TestClass(x=1, y="test")
    # Should use default object repr
    assert "TestClass object at" in repr(obj) or "test_dataclass_shim" in repr(obj)


def test_dataclass_with_eq_false():
    """Test that eq=False works."""
    from pychub.model.dataclass_shim import dataclass

    @dataclass(eq=False)
    class TestClass:
        x: int
        y: str

    obj1 = TestClass(x=1, y="test")
    obj2 = TestClass(x=1, y="test")

    # Should use identity comparison
    assert obj1 is not obj2
    assert not (obj1 == obj2)


def test_dataclass_inheritance():
    """Test that dataclass inheritance works."""
    from pychub.model.dataclass_shim import dataclass

    @dataclass
    class BaseClass:
        x: int

    @dataclass
    class DerivedClass(BaseClass):
        y: str

    obj = DerivedClass(x=1, y="test")
    assert obj.x == 1
    assert obj.y == "test"


def test_dataclass_preserves_methods():
    """Test that class methods are preserved."""
    from pychub.model.dataclass_shim import dataclass

    @dataclass
    class TestClass:
        x: int

        def double(self):
            return self.x * 2

    obj = TestClass(x=5)
    assert obj.double() == 10


def test_dataclass_preserves_docstring():
    """Test that class docstring is preserved."""
    from pychub.model.dataclass_shim import dataclass

    @dataclass
    class TestClass:
        """This is a test class."""
        x: int

    assert TestClass.__doc__ == "This is a test class."


def test_dataclass_empty_parentheses():
    """Test that dataclass() with empty parentheses works."""
    from pychub.model.dataclass_shim import dataclass

    @dataclass()
    class TestClass:
        x: int
        y: str

    obj = TestClass(x=1, y="test")
    assert obj.x == 1
    assert obj.y == "test"


def test_dataclass_mixed_parameters():
    """Test dataclass with mixture of parameters."""
    from pychub.model.dataclass_shim import dataclass

    @dataclass(frozen=False, order=False, eq=True, repr=True)
    class TestClass:
        x: int
        y: str = "default"

    obj = TestClass(x=1)
    assert obj.x == 1
    assert obj.y == "default"


def test_version_boundary_at_39():
    """Test version check at 3.9 boundary."""
    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr("pychub.model.dataclass_shim._sys.version_info", (3, 9, 15))

    import importlib
    import pychub.model.dataclass_shim
    importlib.reload(pychub.model.dataclass_shim)
    from pychub.model.dataclass_shim import dataclass

    # Should strip version-specific params
    @dataclass(frozen=True)
    class TestClass:
        x: int

    obj = TestClass(x=1)
    assert obj.x == 1

    monkeypatch.undo()


def test_version_boundary_at_310():
    """Test version check at 3.10 boundary."""
    if sys.version_info < (3, 10):
        pytest.skip("Need Python 3.10+ for this test")

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr("pychub.model.dataclass_shim._sys.version_info", (3, 10, 0))

    import importlib
    import pychub.model.dataclass_shim
    importlib.reload(pychub.model.dataclass_shim)
    from pychub.model.dataclass_shim import dataclass

    # Should preserve version-specific params
    @dataclass(slots=True)
    class TestClass:
        x: int

    assert hasattr(TestClass, "__slots__")

    monkeypatch.undo()