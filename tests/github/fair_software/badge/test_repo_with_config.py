from tests.contracts.repo import Contract
import pytest
from . import mocker
from howfairis import Platform
from howfairis import Repo


@pytest.fixture
def mocked_repo(mocker):
    with mocker:
        return Repo("https://github.com/fair-software/badge", config_file=".howfairis-custom-config.yml")


class TestRepoWithConfig(Contract):

    def test_api(self, mocked_repo):
        assert mocked_repo.api == "https://api.github.com/repos/fair-software/badge"

    def test_branch(self, mocked_repo):
        assert mocked_repo.branch is None

    def test_config_file(self, mocked_repo):
        assert mocked_repo.config_file == ".howfairis-custom-config.yml"

    def test_default_branch(self, mocked_repo):
        assert mocked_repo.default_branch == "master"

    def test_owner(self, mocked_repo):
        assert mocked_repo.owner == "fair-software"

    def test_path(self, mocked_repo):
        assert mocked_repo.path == ""

    def test_platform(self, mocked_repo):
        assert mocked_repo.platform == Platform.GITHUB

    def test_raw_url_format_string(self, mocked_repo):
        assert mocked_repo.raw_url_format_string == "https://raw.githubusercontent.com/fair-software" + \
                                                         "/badge/master/{0}"

    def test_repo(self, mocked_repo):
        assert mocked_repo.repo == "badge"

    def test_url(self, mocked_repo):
        assert mocked_repo.url == "https://github.com/fair-software/badge"
