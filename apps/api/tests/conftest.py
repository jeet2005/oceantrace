import os

import pytest


@pytest.fixture(autouse=True, scope="session")
def set_test_environment() -> None:
    os.environ["OT_ENVIRONMENT"] = "test"
    yield
    os.environ.pop("OT_ENVIRONMENT", None)