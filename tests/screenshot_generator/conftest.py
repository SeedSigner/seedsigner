import pytest



def pytest_addoption(parser):
    parser.addoption("--locale", action="store", default=None)
    parser.addoption("--overflow-scan", action="store_true", default=False)
    parser.addoption("--overflow-json", action="store", default=None,
                     help="also write the overflow events to this path as JSON")


@pytest.fixture(scope='session')
def target_locale(request):
    return request.config.option.locale


@pytest.fixture(scope='session')
def overflow_scan(request):
    return request.config.option.overflow_scan


@pytest.fixture(scope='session')
def overflow_json(request):
    return request.config.option.overflow_json
