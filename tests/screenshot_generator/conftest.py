import pytest

from seedsigner.models.settings_definition import SettingsConstants



def pytest_addoption(parser):
    parser.addoption("--locale", action="store", default=None)
    parser.addoption("--resolution", action="store", default=None, help="Render at a specific width and height; enter as \"320x240\", \"480x320\", etc.")
    parser.addoption("--no-clean", action="store_true", help="Do not wipe the screenshots directory before running tests.")


@pytest.fixture(scope='session')
def target_locale(request):
    locale = request.config.option.locale
    if locale and locale not in [lc for lc,_ in SettingsConstants.get_detected_languages()]:
        pytest.fail(f"Invalid --locale: \"{locale}\". Must be one of {', '.join(sorted([lc for lc,_ in SettingsConstants.get_detected_languages()]))}")

    return request.config.option.locale


@pytest.fixture(scope='session')
def target_resolution(request):
    resolution = request.config.option.resolution
    if resolution is None:
        return None
    try:
        resolution_dims = resolution.split("x")
        return (int(resolution_dims[0]), int(resolution_dims[1]))
    except Exception:
        pytest.fail(f"Invalid --resolution: {target_resolution}. Must be in the form \"WIDTHxHEIGHT\" (e.g. 320x240)")


@pytest.fixture(scope='session')
def no_clean(request):
    return request.config.getoption("--no-clean")
