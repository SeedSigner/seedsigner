import pytest



def pytest_addoption(parser):
    parser.addoption("--locale", action="store", default=None)


@pytest.fixture(scope='session')
def target_locale(request):
    return request.config.option.locale
