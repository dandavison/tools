"""Pytest configuration for tools tests."""

import pytest


def pytest_configure(config):
    config.addinivalue_line("markers", "functional: mark test as functional (hits external services)")


def pytest_addoption(parser):
    parser.addoption(
        "--skip-functional",
        action="store_true",
        default=False,
        help="Skip functional tests that hit external services",
    )


def pytest_collection_modifyitems(config, items):
    if config.getoption("--skip-functional"):
        skip_functional = pytest.mark.skip(reason="--skip-functional option provided")
        for item in items:
            if "functional" in item.keywords:
                item.add_marker(skip_functional)

