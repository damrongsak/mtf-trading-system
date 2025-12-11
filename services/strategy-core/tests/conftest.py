import os
import pytest

# Set dummy DATABASE_URL before importing modules that use it
os.environ["DATABASE_URL"] = "sqlite:///:memory:"

@pytest.fixture(scope="session", autouse=True)
def set_test_env():
    """
    Ensure environment variables are set for testing.
    """
    os.environ["DATABASE_URL"] = "sqlite:///:memory:"
