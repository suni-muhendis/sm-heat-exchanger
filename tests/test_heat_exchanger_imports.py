import pytest

def test_imports():
    try:
        import ht
        import fluids
    except ImportError as e:
        pytest.fail(f"Required package not found: {e}")
