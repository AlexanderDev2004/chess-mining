from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import polars as pl

from chess_mining.ingestion.pgn_reader import iter_games
from chess_mining.ingestion.schema import GAME_SCHEMA


@dataclass
class IngestionStats:
    """Statistics collected during an ingestion run."""

    total_games: int = 0
    batches_written: int = 0
    parser_errors: int = 0
    malformed_games: int = 0
    missing_elo: int = 0
    missing_opening: int = 0
    output_dir: Path = field(default_factory=Path)
    output_size_bytes: int = 0

    def format_report(self) -> str:
        return "\n".join(
            [
                "Ingestion statistics",
                f"  Games processed:        {self.total_games:,}",
                f"  Batches written:        {self.batches_written:,}",
                f"  Parser errors:          {self.parser_errors:,}",
                f"  Malformed games:        {self.malformed_games:,}",
                f"  Games with missing Elo: {self.missing_elo:,}",
                f"  Games missing opening:  {self.missing_opening:,}",
                f"  Output directory:       {self.output_dir}",
                f"  Output size:            {self.output_size_bytes:,} bytes",
            ]
        )


def ingest_to_parquet(
    source: str | Path,
    output_dir: str | Path,
    batch_size: int = 10_000,
    max_games: int | None = None,
    overwrite: bool = False,
) -> IngestionStats:
    """Stream games from a PGN source into batched Parquet files."""
    if batch_size <= 0:
        raise ValueError(f"batch_size must be greater than zero, got {batch_size}")

    source = Path(source)
    output_dir = Path(output_dir)

    if not source.exists():
        raise FileNotFoundError(f"PGN file not found: {source}")

    _guard_existing_output(output_dir, overwrite)
    output_dir.mkdir(parents=True, exist_ok=True)

    stats = IngestionStats(output_dir=output_dir)
    batch: list[dict] = []

    for game in iter_games(source, max_games=max_games):
        batch.append(game)
        stats.total_games += 1
        stats.parser_errors += game["parser_error_count"]

        if game["parser_error_count"] > 0 or game["result"] is None:
            stats.malformed_games += 1

        if game["white_elo"] is None or game["black_elo"] is None:
            stats.missing_elo += 1

        if game["eco"] is None or game["opening"] is None:
            stats.missing_opening += 1

        if len(batch) >= batch_size:
            stats.batches_written += 1
            _write_batch(batch, output_dir, stats.batches_written)
            batch.clear()
            print(f"Processed {stats.total_games:,} games")

    if batch:
        stats.batches_written += 1
        _write_batch(batch, output_dir, stats.batches_written)
        batch.clear()

    stats.output_size_bytes = sum(
        path.stat().st_size for path in sorted(output_dir.glob("part-*.parquet"))
    )

    return stats


def _guard_existing_output(output_dir: Path, overwrite: bool) -> None:
    if overwrite:
        return

    existing = sorted(output_dir.glob("part-*.parquet")) if output_dir.exists() else []
    if existing:
        names = ", ".join(path.name for path in existing[:3])
        more = " ..." if len(existing) > 3 else ""
        raise FileExistsError(
            f"Output directory {output_dir} already contains Parquet parts "
            f"({names}{more}). Pass overwrite=True (or --overwrite) to replace "
            "them, or choose a different output directory."
        )


def _write_batch(
    batch: list[dict],
    output_dir: Path,
    part_number: int,
) -> None:
    dataframe = pl.DataFrame(
        batch,
        schema=GAME_SCHEMA,
    )

    output_path = output_dir / f"part-{part_number:05d}.parquet"
    dataframe.write_parquet(output_path, compression="zstd")
