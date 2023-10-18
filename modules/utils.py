from configparser import ConfigParser
from contextlib import closing
import sqlite3
from pathlib import Path


def get_project_root() -> Path:
    return Path(__file__).parent.parent.resolve()


def get_config_info(query: str | None = None):
    parser = ConfigParser()
    parser.read("./config.ini")
    sections = parser.sections()
    if query is None:
        return sections
    if query in sections:
        return dict(parser[query])
    else:
        return None


def init_project():
    root_path = get_project_root()
    setup_sql = root_path / "modules" / "setup.sql"
    database_path = root_path / "database"
    log_path = root_path / "log"
    arcaea_log_path = log_path / "arcaea.log"

    if not database_path.exists():
        database_path.mkdir(exist_ok=False)
        yoffline_db_path = database_path / "yoffline.db"
        with closing(sqlite3.connect(yoffline_db_path)) as con:
            with con:
                with open(setup_sql) as f:
                    setup_script = f.read()
                    con.executescript(setup_script)

    log_path.mkdir(exist_ok=True)
    arcaea_log_path.touch(exist_ok=True)
