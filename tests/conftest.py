from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
import zstandard

SAMPLE_GAME = """\
[Event "Rated Blitz"]
[Site "https://lichess.org/abcdefgh"]
[Date "2024.01.01"]
[Round "-"]
[White "Alice"]
[Black "Bob"]
[Result "1-0"]
[WhiteElo "2000"]
[BlackElo "1800"]
[ECO "C00"]
[Opening "French Defense"]
[TimeControl "300+0"]
[Termination "Normal"]

1. e4 e6 2. d4 d5 1-0
"""

# Missing: ECO, Opening, TimeControl, Termination; provisional Elo values.
DRAW_GAME = """\
[Event "Rated Rapid"]
[Site "https://lichess.org/ijklmnop"]
[Date "2024.01.02"]
[Round "-"]
[White "Carol"]
[Black "Dave"]
[Result "1/2-1/2"]
[WhiteElo "?"]
[BlackElo "?"]

1. d4 d5 1/2-1/2
"""


def write_pgn(path: Path, content: str) -> Path:
    path.write_text(textwrap.dedent(content), encoding="utf-8")
    return path


def write_pgn_zst(path: Path, content: str) -> Path:
    data = textwrap.dedent(content).encode("utf-8")
    path.write_bytes(zstandard.ZstdCompressor().compress(data))
    return path


@pytest.fixture
def sample_pgn(tmp_path: Path) -> Path:
    return write_pgn(tmp_path / "games.pgn", SAMPLE_GAME)


@pytest.fixture
def two_game_pgn(tmp_path: Path) -> Path:
    return write_pgn(tmp_path / "games.pgn", SAMPLE_GAME + "\n\n" + DRAW_GAME)
