# Chess Mining

A chess data mining pipeline built on the [Lichess Open Database](https://database.lichess.org).
The first stage ingests a monthly dump of standard rated games (PGN, optionally
Zstandard-compressed) and converts it into columnar Parquet files for analysis.

## Tech Stack

- Python 3.13
- [uv](https://docs.astral.sh/uv/) for dependency and environment management
- [python-chess](https://python-chess.readthedocs.io/) for PGN parsing
- [zstandard](https://github.com/python-zstandard) for `.pgn.zst` decompression
- [Polars](https://pola.rs/) for DataFrame processing
- [PyArrow](https://arrow.apache.org/docs/python/) for Parquet compatibility
- pytest for testing, Ruff for linting and formatting

## Dataset

Downloads are available at <https://database.lichess.org#standard>. Example:

- File: `lichess_db_standard_rated_2026-10.pgn.zst`
- Place downloads in `data/raw/`

## Installation

Requires [uv](https://docs.astral.sh/uv/getting-started/installation/). From the
repository root:

```powershell
uv sync
```

This creates the virtual environment, installs all dependencies including the
project itself in editable mode, and makes the modules below available.

## Project Structure

```text
chess-mining/
├── data/
│   ├── raw/          # downloaded dataset files
│   ├── interim/      # intermediate artifacts
│   └── processed/    # Parquet output
├── notebooks/        # exploration notebooks
├── tests/            # pytest suite with synthetic PGN fixtures
└── src/chess_mining/
    ├── ingestion/
    │   ├── pgn_reader.py   # streaming PGN / PGN.ZST reader
    │   ├── schema.py       # Polars schema for game metadata
    │   ├── writer.py       # batched Parquet writer + ingestion statistics
    │   └── __main__.py     # ingestion CLI
    └── inspect.py          # Parquet inspection CLI
```

## Running Ingestion

```powershell
uv run python -m chess_mining.ingestion --help
```

Full run over the monthly dump:

```powershell
uv run python -m chess_mining.ingestion `
  --input data/raw/lichess_db_standard_rated_2026-10.pgn.zst `
  --output data/processed/games `
  --batch-size 10000
```

Options:

| Option | Description |
| --- | --- |
| `--input` (required) | Path to a `.pgn` or `.pgn.zst` file |
| `--output` | Output directory for Parquet parts (default: `data/processed/games`) |
| `--batch-size` | Games per Parquet part file (default: `10000`) |
| `--max-games` | Limit the number of games ingested (useful for smoke tests) |
| `--overwrite` | Replace existing Parquet parts in the output directory |

The ingestion streams the source: only one game at a time and one batch of
records are held in memory, never the whole dataset. Output parts are named
`part-00001.parquet`, `part-00002.parquet`, and so on. If the output directory
already contains parts, the run aborts unless `--overwrite` is given.

At the end of a run a summary is printed with the total games processed,
batches written, parser errors, malformed games, games with missing Elo or
opening metadata, the output directory, and the total output size.

## Inspecting Parquet Output

```powershell
uv run python -m chess_mining.inspect data/processed/games
```

The path can be a directory of `part-*.parquet` files or a single Parquet
file. The report shows the row and column count, the schema, the first five
records, the result distribution, and the average White/Black Elo excluding
missing values.

## Running Tests

The test suite uses small synthetic PGN fixtures and never touches the real
dataset.

```powershell
uv run pytest -v
```

Lint and format checks:

```powershell
uv run ruff check .
uv run ruff format --check .
```

## Notes

- Missing or invalid Elo values (`?`, non-numeric) are stored as nulls.
- Missing optional headers (ECO, Opening, TimeControl, ...) are stored as nulls
  and counted; records are never discarded for missing optional headers.
- Games with parser errors are kept and flagged (`parser_error_count`), and the
  ingestion continues with the following games.
