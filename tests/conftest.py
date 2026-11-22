import pytest

from sfm_fx_new_age.testing.fixtures import fixture_runtime


@pytest.fixture
def runtime():
    value = fixture_runtime()
    try:
        yield value
    finally:
        value.close()
