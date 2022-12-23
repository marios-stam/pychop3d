import pytest

from pychop3d.configuration import Configuration, config


@pytest.fixture(scope='function')
def config():

    yield config
    config.restore_defaults()
