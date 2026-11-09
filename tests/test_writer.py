from __future__ import annotations

import textwrap
from pathlib import Path

import polars as pl
import pytest
from conftest import DRAW_GAME, SAMPLE_GAME

from chess_mining.ingestion.schema import GAME_SCHEMA
from chess_mining.ingestion.writer import ingest_to_parquet


def _repeated_pgn(count: int) -> str:
    return "\n\n".join(SAMPLE_GAME for _ in range(count))


def test_writes_batched_parts(tmp_path: Path) -> None:
    source = tmp_path / "games.pgn"
    source.write_text(_repeated_pgn(5), encoding="utf-8")
    output = tmp_path / "out"

    stats = ingest_to_parquet(source, output, batch_size=2)

    parts = sorted(output.glob("part-*.parquet"))
    assert [path.name for path in parts] == [
        "part-00001.parquet",
        "part-00002.parquet",
        "part-00003.parquet",
    ]
    assert [pl.read_parquet(path).height for path in parts] == [2, 2, 1]
    assert stats.total_games == 5
    assert stats.batches_written == 3


def test_preserves_schema_with_missing_metadata(tmp_path: Path) -> None:
    source = tmp_path / "games.pgn"
    source.write_text(SAMPLE_GAME + "\n\n" + DRAW_GAME, encoding="utf-8")
    output = tmp_path / "out"

    ingest_to_parquet(source, output, batch_size=10)

    df = pl.read_parquet(output / "part-00001.parquet")
    assert df.height == 2
    assert dict(df.schema) == GAME_SCHEMA

    draw_row = df.row(1, named=True)
    assert draw_row["eco"] is None
    assert draw_row["opening"] is None
    assert draw_row["white_elo"] is None
    assert draw_row["black_elo"] is None


def test_refuses_to_overwrite_existing_output(tmp_path: Path) -> None:
    source = tmp_path / "games.pgn"
    source.write_text(SAMPLE_GAME, encoding="utf-8")
    output = tmp_path / "out"

    ingest_to_parquet(source, output, batch_size=10)

    with pytest.raises(FileExistsError, match="already contains Parquet parts"):
        ingest_to_parquet(source, output, batch_size=10)

    # Explicit overwrite replaces the previous parts.
    stats = ingest_to_parquet(source, output, batch_size=10, overwrite=True)
    assert stats.total_games == 1
    assert stats.batches_written == 1


def test_reports_ingestion_statistics(tmp_path: Path) -> None:
    source = tmp_path / "games.pgn"
    source.write_text(SAMPLE_GAME + "\n\n" + DRAW_GAME, encoding="utf-8")
    output = tmp_path / "out"

    stats = ingest_to_parquet(source, output, batch_size=10)

    assert stats.total_games == 2
    assert stats.parser_errors == 0
    assert stats.missing_elo == 1
    assert stats.missing_opening == 1
    assert stats.output_size_bytes > 0
    assert stats.output_dir == output

    report = stats.format_report()
    assert "Games processed" in report
    assert "Batches written" in report
    assert "Output size" in report


def test_counts_parser_errors_in_statistics(tmp_path: Path) -> None:
    broken = textwrap.dedent("""\
        [Event "Broken"]
        [Site "?"]
        [Date "????.??.??"]
        [Round "?"]
        [White "X"]
        [Black "Y"]
        [Result "*"]

        1. e4 e5 2. Bb5 3. Nf3 *
        """)
    source = tmp_path / "games.pgn"
    source.write_text(broken + "\n" + SAMPLE_GAME, encoding="utf-8")
    output = tmp_path / "out"

    stats = ingest_to_parquet(source, output, batch_size=10)

    assert stats.total_games == 2
    assert stats.parser_errors == 1
    assert stats.malformed_games == 1


def test_rejects_invalid_batch_size(tmp_path: Path) -> None:
    source = tmp_path / "games.pgn"
    source.write_text(SAMPLE_GAME, encoding="utf-8")

    with pytest.raises(ValueError, match="batch_size"):
        ingest_to_parquet(source, tmp_path / "out", batch_size=0)


def test_rejects_missing_source(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        ingest_to_parquet(tmp_path / "missing.pgn", tmp_path / "out")
