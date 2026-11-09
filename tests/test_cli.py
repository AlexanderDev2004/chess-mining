from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from conftest import SAMPLE_GAME

from chess_mining.ingestion.__main__ import main


@pytest.mark.parametrize(
    ("argv", "message"),
    [
        (["--input", "does_not_exist.pgn"], "input file does not exist"),
        (["--input"], "expected one argument"),
        (["--input", __file__, "--batch-size", "0"], "greater than zero"),
        (["--input", __file__, "--max-games", "0"], "greater than zero"),
    ],
)
def test_cli_rejects_invalid_arguments(
    argv: list[str], message: str, capsys: pytest.CaptureFixture
) -> None:
    with pytest.raises(SystemExit) as excinfo:
        main(argv)

    assert excinfo.value.code == 2
    assert message in capsys.readouterr().err


def test_cli_runs_small_ingestion(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    source = tmp_path / "games.pgn"
    source.write_text(SAMPLE_GAME, encoding="utf-8")
    output = tmp_path / "out"

    main(["--input", str(source), "--output", str(output), "--batch-size", "1"])

    out = capsys.readouterr().out
    assert "Games processed:        1" in out
    assert (output / "part-00001.parquet").exists()


def test_cli_refuses_existing_output(
    tmp_path: Path, capsys: pytest.CaptureFixture
) -> None:
    source = tmp_path / "games.pgn"
    source.write_text(SAMPLE_GAME, encoding="utf-8")
    output = tmp_path / "out"

    main(["--input", str(source), "--output", str(output)])

    with pytest.raises(SystemExit) as excinfo:
        main(["--input", str(source), "--output", str(output)])

    assert excinfo.value.code == 2
    assert "already contains Parquet parts" in capsys.readouterr().err


def test_cli_help_shows_options() -> None:
    result = subprocess.run(
        [sys.executable, "-m", "chess_mining.ingestion", "--help"],
        capture_output=True,
        text=True,
        check=True,
    )

    for option in ("--input", "--output", "--batch-size", "--max-games", "--overwrite"):
        assert option in result.stdout
