from loguru import logger
import sqlite3
from ..utils import get_config_info, get_project_root

project_root = get_project_root()
log_path = project_root / "log"
log_path.mkdir(exist_ok=True)
log_file = log_path / "Arcaea.log"
log_file.touch(exist_ok=True)

# log_level = "DEBUG"
config_arcaea = get_config_info("Arcaea")
if isinstance(config_arcaea, dict):
    log_level = config_arcaea["loglevel"]
    arcsong_path = project_root / config_arcaea["dbpath"]
    userdb_path = project_root / config_arcaea["userdbpath"]
else:
    logger.error("Section [Arcaea] not found in config")
logger.add(log_file, level=log_level, rotation="20 MB")

# db_path = project_root / "Arcaea" / "ArcaeaSongDatabase"

# user_db_path = project_root / "Arcaea" / "user.db"
if not userdb_path.exists():
    con = sqlite3.connect(userdb_path)
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
