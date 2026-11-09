from __future__ import annotations

import argparse
from pathlib import Path

from chess_mining.ingestion.writer import ingest_to_parquet


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m chess_mining.ingestion",
        description="Ingest Lichess PGN data into batched Parquet files.",
    )

    parser.add_argument(
        "--input",
        type=Path,
        required=True,
        help="Path to a PGN or .pgn.zst file",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=Path("data/processed/games"),
        help="Output directory for Parquet parts (default: data/processed/games)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10_000,
        help="Number of games per Parquet part file (default: 10000)",
    )
    parser.add_argument(
        "--max-games",
        type=int,
        default=None,
        help="Limit the number of games ingested (useful for testing)",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Replace existing Parquet part files in the output directory",
    )

    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if not args.input.exists():
        parser.error(f"input file does not exist: {args.input}")

    if not args.input.is_file():
        parser.error(f"input is not a file: {args.input}")

    if args.batch_size <= 0:
        parser.error("--batch-size must be greater than zero")

    if args.max_games is not None and args.max_games <= 0:
        parser.error("--max-games must be greater than zero")

    try:
        stats = ingest_to_parquet(
            source=args.input,
            output_dir=args.output,
            batch_size=args.batch_size,
            max_games=args.max_games,
            overwrite=args.overwrite,
        )
    except FileExistsError as error:
        parser.error(str(error))

    print(stats.format_report())


if __name__ == "__main__":
    main()
