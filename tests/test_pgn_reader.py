from __future__ import annotations

import textwrap
from pathlib import Path

import pytest
from conftest import DRAW_GAME, SAMPLE_GAME, write_pgn, write_pgn_zst

from chess_mining.ingestion.pgn_reader import (
    iter_games,
    normalize_result,
    open_pgn,
    parse_int,
)


def test_parses_valid_game(sample_pgn: Path) -> None:
    games = list(iter_games(sample_pgn))

    assert len(games) == 1
    game = games[0]
    assert game["game_id"] == 1
    assert game["white"] == "Alice"
    assert game["black"] == "Bob"
    assert game["white_elo"] == 2000
    assert game["black_elo"] == 1800
    assert game["result"] == "1-0"
    assert game["eco"] == "C00"
    assert game["opening"] == "French Defense"
    assert game["event"] == "Rated Blitz"
    assert game["time_control"] == "300+0"
    assert game["termination"] == "Normal"
    assert game["variant"] == "Standard"


def test_total_ply_count(sample_pgn: Path) -> None:
    (game,) = iter_games(sample_pgn)
    # 1. e4 e6 2. d4 d5 -> four half-moves
    assert game["total_plies"] == 4


def test_multiple_games(two_game_pgn: Path) -> None:
    games = list(iter_games(two_game_pgn))

    assert len(games) == 2
    assert [game["game_id"] for game in games] == [1, 2]
    assert games[0]["white"] == "Alice"
    assert games[1]["white"] == "Carol"
    assert games[1]["result"] == "1/2-1/2"


def test_max_games_limit(two_game_pgn: Path) -> None:
    games = list(iter_games(two_game_pgn, max_games=1))

    assert len(games) == 1
    assert games[0]["white"] == "Alice"


def test_empty_input(tmp_path: Path) -> None:
    path = write_pgn(tmp_path / "empty.pgn", "")

    assert list(iter_games(path)) == []


def test_missing_optional_headers(tmp_path: Path) -> None:
    minimal = """\
    [Event "Minimal"]
    [White "A"]
    [Black "B"]
    [Result "*"]

    1. e4 *
    """
    path = write_pgn(tmp_path / "minimal.pgn", minimal)

    (game,) = iter_games(path)

    # python-chess fills the Seven Tag Roster with "?" placeholders when the
    # header is absent; optional tags beyond it stay None.
    assert game["site"] == "?"
    assert game["date"] == "????.??.??"
    assert game["round"] == "?"
    assert game["eco"] is None
    assert game["opening"] is None
    assert game["time_control"] is None
    assert game["termination"] is None
    assert game["variant"] == "Standard"
    assert game["total_plies"] == 1


@pytest.mark.parametrize(
    ("white_elo", "black_elo", "expected"),
    [
        ('[WhiteElo "?"]', '[BlackElo "1800"]', (None, 1800)),
        ('[WhiteElo "abc"]', '[BlackElo "1800"]', (None, 1800)),
        ('[WhiteElo ""]', '[BlackElo "1800"]', (None, 1800)),
        ("", "", (None, None)),
    ],
)
def test_missing_or_invalid_elo(
    tmp_path: Path,
    white_elo: str,
    black_elo: str,
    expected: tuple[int | None, int | None],
) -> None:
    headers = "\n".join(
        line
        for line in [
            '[Event "Elos"]',
            '[White "A"]',
            '[Black "B"]',
            '[Result "1-0"]',
            white_elo,
            black_elo,
        ]
        if line
    )
    path = write_pgn(tmp_path / "elos.pgn", f"{headers}\n\n1. e4 e6 1-0\n")

    (game,) = iter_games(path)

    assert (game["white_elo"], game["black_elo"]) == expected


def test_skips_placeholder_games_from_extra_blank_lines(tmp_path: Path) -> None:
    # Extra blank-line separators must not emit junk records.
    path = write_pgn(
        tmp_path / "spaced.pgn",
        SAMPLE_GAME + "\n\n\n\n" + DRAW_GAME,
    )

    games = list(iter_games(path))

    assert [game["game_id"] for game in games] == [1, 2]
    assert games[0]["white"] == "Alice"
    assert games[1]["white"] == "Carol"


def test_malformed_movetext_does_not_stop_ingestion(tmp_path: Path) -> None:
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
    content = broken + "\n" + SAMPLE_GAME
    path = write_pgn(tmp_path / "broken.pgn", content)

    games = list(iter_games(path))

    assert len(games) == 2
    assert games[0]["parser_error_count"] == 1
    assert games[0]["event"] == "Broken"
    assert games[1]["event"] == "Rated Blitz"
    assert games[1]["parser_error_count"] == 0


def test_reads_zst_compressed_pgn(tmp_path: Path) -> None:
    path = write_pgn_zst(tmp_path / "games.pgn.zst", SAMPLE_GAME)

    games = list(iter_games(path))

    assert len(games) == 1
    assert games[0]["white"] == "Alice"
    assert games[0]["white_elo"] == 2000


def test_open_pgn_rejects_missing_file(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        list(iter_games(tmp_path / "nope.pgn"))


@pytest.mark.parametrize(
    ("value", "expected"),
    [("", None), (None, None), ("?", None), ("abc", None), ("1500", 1500)],
)
def test_parse_int(value: str | None, expected: int | None) -> None:
    assert parse_int(value) == expected


def test_normalize_result() -> None:
    assert normalize_result("1-0") == "1-0"
    assert normalize_result("0-1") == "0-1"
    assert normalize_result("1/2-1/2") == "1/2-1/2"
    assert normalize_result("*") == "*"
    assert normalize_result("1-0 ") is None
    assert normalize_result("won") is None
    assert normalize_result(None) is None


def test_open_pgn_plain_text(sample_pgn: Path) -> None:
    with open_pgn(sample_pgn) as handle:
        assert "[Event" in handle.readline()
