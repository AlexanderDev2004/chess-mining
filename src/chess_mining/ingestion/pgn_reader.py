from __future__ import annotations

import io
from collections.abc import Iterator
from pathlib import Path
from typing import TextIO

import chess.pgn
import zstandard

VALID_RESULTS = frozenset({"1-0", "0-1", "1/2-1/2", "*"})

# python-chess fills the Seven Tag Roster with these placeholders when a
# header is absent; a game whose headers still equal them, without moves or
# errors, is formatting noise rather than a real game.
_EMPTY_GAME_HEADERS = dict(chess.pgn.Headers())


def open_pgn(path: Path) -> TextIO:
    """Open a plain PGN or Zstandard-compressed PGN as a text stream."""
    if path.suffix == ".zst":
        raw = path.open("rb")
        reader = zstandard.ZstdDecompressor().stream_reader(raw)
        return io.TextIOWrapper(reader, encoding="utf-8", errors="replace")

    return path.open("r", encoding="utf-8", errors="replace")


def parse_int(value: str | None) -> int | None:
    """Parse an integer header value, returning None for missing/invalid values."""
    if not value or value == "?":
        return None

    try:
        return int(value)
    except ValueError:
        return None


def normalize_result(value: str | None) -> str | None:
    """Return the result if it is a valid PGN result token, otherwise None."""
    return value if value in VALID_RESULTS else None


def _is_empty_game(game: chess.pgn.Game) -> bool:
    return (
        not game.errors
        and game.end().ply() == 0
        and dict(game.headers) == _EMPTY_GAME_HEADERS
    )


def iter_games(
    path: str | Path,
    max_games: int | None = None,
) -> Iterator[dict]:
    """Yield game metadata one game at a time, streaming from the source file."""
    source = Path(path)

    if not source.exists():
        raise FileNotFoundError(f"PGN file not found: {source}")

    count = 0

    with open_pgn(source) as handle:
        while max_games is None or count < max_games:
            try:
                game = chess.pgn.read_game(handle)
            except Exception:  # noqa: BLE001
                # read_game logs recoverable problems on the game object; an
                # exception here means the stream state is no longer reliable.
                # Stop instead of risking a corrupt or infinite loop.
                break

            if game is None:
                break

            if _is_empty_game(game):
                # Consecutive blank lines or stray separators produce a
                # placeholder game with defaulted headers; skip it instead of
                # emitting a junk record.
                continue

            headers = game.headers
            result = normalize_result(headers.get("Result"))

            yield {
                "game_id": count + 1,
                "event": headers.get("Event"),
                "site": headers.get("Site"),
                "date": headers.get("Date"),
                "round": headers.get("Round"),
                "white": headers.get("White"),
                "black": headers.get("Black"),
                "white_elo": parse_int(headers.get("WhiteElo")),
                "black_elo": parse_int(headers.get("BlackElo")),
                "result": result,
                "eco": headers.get("ECO"),
                "opening": headers.get("Opening"),
                "time_control": headers.get("TimeControl"),
                "termination": headers.get("Termination"),
                "variant": headers.get("Variant", "Standard"),
                "total_plies": max(0, game.end().ply()),
                "parser_error_count": len(game.errors),
            }

            count += 1
