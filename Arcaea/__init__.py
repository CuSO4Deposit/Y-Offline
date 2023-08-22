from loguru import logger
from pathlib import Path
import sqlite3


Path("./log/").mkdir(exist_ok=True)
log_file = Path("./log/Arcaea.log")
log_file.touch(exist_ok=True)

log_level = "DEBUG"
logger.add(log_file, level=log_level, rotation="20 MB")

db_path = Path("./Arcaea/ArcaeaSongDatabase/")

user_db_path = db_path / "user.db"
if not user_db_path.exists():
    con = sqlite3.connect(user_db_path)
    cur = con.cursor()
    cur.executescript(
        """\
BEGIN;
CREATE TABLE record(
        [song_id] TEXT NOT NULL,
        [rating_class] INTEGER NOT NULL DEFAULT 2,
        [pure] INTEGER NOT NULL,
        [max_pure] INTEGER NOT NULL,
        [far] INTEGER NOT NULL, 
        [play_ptt] FLOAT NOT NULL,
        [time] INTEGER NOT NULL,
        [user] TEXT NOT NULL,
        PRIMARY KEY([time], [user]));
CREATE TABLE best(
        [song_id] TEXT NOT NULL,
        [rating_class] INTEGER NOT NULL DEFAULT 2,
        [pure] INTEGER NOT NULL,
        [max_pure] INTEGER NOT NULL,
        [far] INTEGER NOT NULL,
        [play_ptt] REAL NOT NULL,
        [time] INTEGER NOT NULL,
        [user] TEXT NOT NULL,
        PRIMARY KEY([time], [user]));
CREATE TABLE recent(
        [song_id] TEXT NOT NULL,
        [rating_class] INTEGER NOT NULL DEFAULT 2,
        [pure] INTEGER NOT NULL,
        [max_pure] INTEGER NOT NULL,
        [far] INTEGER NOT NULL,
        [play_ptt] REAL NOT NULL,
        [time] INTEGER NOT NULL,
        [user] TEXT NOT NULL,
        PRIMARY KEY([time], [user]));
COMMIT;
"""
    )
