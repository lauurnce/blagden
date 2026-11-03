from typer.testing import CliRunner

import blagden
from blagden.cli import app


def test_package_has_version() -> None:
    assert blagden.__version__ == "0.0.1"


def test_cli_prints_version() -> None:
    result = CliRunner().invoke(app, ["version"])
    assert result.exit_code == 0
    assert result.stdout.strip() == blagden.__version__
