import pytest

from app import limiter


@pytest.fixture(autouse=True)
def reset_rate_limits():
    limiter.reset()
