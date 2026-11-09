from __future__ import annotations

from pathlib import Path

import pytest
from conftest import DRAW_GAME, SAMPLE_GAME

from chess_mining.ingestion.writer import ingest_to_parquet
from chess_mining.inspect import describe


@pytest.fixture
def output_dir(tmp_path: Path) -> Path:
    source = tmp_path / "games.pgn"
    source.write_text(SAMPLE_GAME + "\n\n" + DRAW_GAME, encoding="utf-8")
    output = tmp_path / "out"
    ingest_to_parquet(source, output, batch_size=10)
    return output


def test_describes_directory(output_dir: Path, capsys: pytest.CaptureFixture) -> None:
    report = describe(output_dir)

    assert "Rows:    2" in report
    assert "Columns: 17" in report
    assert "white_elo: Int64" in report
    assert "Alice" in report
    assert "1-0: 1" in report
    assert "1/2-1/2: 1" in report
    assert "Average White Elo: 2000.0" in report
    assert "Average Black Elo: 1800.0" in report


def test_describes_single_file(output_dir: Path) -> None:
    report = describe(output_dir / "part-00001.parquet")

    assert "Rows:    2" in report


def test_missing_directory_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        describe(tmp_path / "nowhere")


def test_empty_directory_raises(tmp_path: Path) -> None:
    empty = tmp_path / "empty"
    empty.mkdir()

    with pytest.raises(FileNotFoundError, match="no part-.*parquet"):
        describe(empty)
