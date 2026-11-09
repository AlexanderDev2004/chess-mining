from __future__ import annotations

import argparse
from pathlib import Path

import polars as pl


def load_parquet(path: Path) -> pl.DataFrame:
    """Load one Parquet file or every part-*.parquet file in a directory."""
    if path.is_dir():
        files = sorted(path.glob("part-*.parquet"))
        if not files:
            raise FileNotFoundError(f"no part-*.parquet files found in {path}")
        return pl.scan_parquet(files).collect()

    if not path.exists():
        raise FileNotFoundError(f"Parquet file not found: {path}")

    return pl.read_parquet(path)


def describe(path: str | Path) -> str:
    """Build a summary report for Parquet output."""
    source = Path(path)
    df = load_parquet(source)

    lines = [
        f"Parquet inspection: {source}",
        f"  Rows:    {df.height:,}",
        f"  Columns: {df.width}",
        "  Schema:",
    ]

    for name, dtype in df.schema.items():
        lines.append(f"    {name}: {dtype}")

    lines.append("  First 5 records:")
    for row in df.head(5).iter_rows(named=True):
        fields = ", ".join(f"{key}={value!r}" for key, value in row.items())
        lines.append(f"    {fields}")

    lines.append("  Result distribution:")
    distribution = df.group_by("result").agg(pl.len().alias("games")).sort("result")
    for row in distribution.iter_rows(named=True):
        lines.append(f"    {row['result']}: {row['games']:,}")

    white_mean = df["white_elo"].mean()
    black_mean = df["black_elo"].mean()
    lines.append(
        f"  Average White Elo: {white_mean:.1f}"
        if white_mean is not None
        else "  Average White Elo: n/a"
    )
    lines.append(
        f"  Average Black Elo: {black_mean:.1f}"
        if black_mean is not None
        else "  Average Black Elo: n/a"
    )

    return "\n".join(lines)


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(
        prog="python -m chess_mining.inspect",
        description="Inspect Parquet output produced by the ingestion pipeline.",
    )
    parser.add_argument(
        "path",
        type=Path,
        help="A Parquet file or a directory containing part-*.parquet files",
    )

    args = parser.parse_args(argv)

    try:
        print(describe(args.path))
    except FileNotFoundError as error:
        parser.error(str(error))


if __name__ == "__main__":
    main()
