"""Smoke tests for Phase 1 package structure."""

import flagmatrix_api
import flagmatrix_cli
import flagmatrix_core


def test_package_imports() -> None:
    assert flagmatrix_core.__version__ == "0.1.0"
    assert flagmatrix_cli.__version__ == "0.1.0"
    assert flagmatrix_api.__version__ == "0.1.0"
