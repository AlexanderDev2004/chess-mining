import polars as pl

GAME_SCHEMA = {
    "game_id": pl.UInt64,
    "event": pl.String,
    "site": pl.String,
    "date": pl.String,
    "round": pl.String,
    "white": pl.String,
    "black": pl.String,
    "white_elo": pl.Int64,
    "black_elo": pl.Int64,
    "result": pl.String,
    "eco": pl.String,
    "opening": pl.String,
    "time_control": pl.String,
    "termination": pl.String,
    "variant": pl.String,
    "total_plies": pl.UInt32,
    "parser_error_count": pl.UInt32,
}
