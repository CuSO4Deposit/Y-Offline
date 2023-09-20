from contextlib import closing
import sqlite3
from sys import stderr
from modules.arcaea import utils as arcaea
from modules.utils import get_config_info, get_project_root
from loguru import logger
from pathlib import Path
import pytest
from time import time as current_time


@pytest.fixture(scope="session")
def arcaea_db_manager():
    project_root = get_project_root()
    config = get_config_info("YOffline")
    config_arcaea = get_config_info("Arcaea")
    if not isinstance(config_arcaea, dict):
        logger.error("Section [Arcaea] not found in config")
    if not isinstance(config, dict):
        logger.error("Section [YOffline] not found in config")
    arcsong_path = project_root / config_arcaea["dbpath"]
    userdb_path = Path(__file__).parent / "user.db"
    yield arcaea.ArcaeaDbManager(arcsong_path=arcsong_path, userdb_path=userdb_path)
    userdb_path.unlink()


def test_PlayRecord():
    user_id = "test"
    song_id = "fractureray"
    rating_class = 2
    pure = 1279
    max_pure = 1277
    far = 0
    time = 1

    record = arcaea.playRecord(
        user_id, song_id, rating_class, pure, max_pure, far, time
    )
    assert record.score == 10001277
    assert record.play_ptt == 13.3

    pure = 1278
    far = 1
    record = arcaea.playRecord(
        user_id,
        song_id,
        rating_class,
        pure,
        max_pure,
        far,
        int(current_time()),
    )
    assert record.score == 9997367
    assert str(record.time)[0] == "1"


class Test_ArcDbmanager:
    def test__insert(self, arcaea_db_manager: arcaea.ArcaeaDbManager):
        user_id = "test"
        song_id = "fractureray"
        rating_class = 2
        pure = 1279
        max_pure = 1277
        far = 0
        time = 1

        record = arcaea.playRecord(
            user_id, song_id, rating_class, pure, max_pure, far, time
        )
        arcaea_db_manager._insert(table="arcaea_record", record=record)

    def test_sqlite_empty_query(self, arcaea_db_manager: arcaea.ArcaeaDbManager):
        """test if sqlite supports empty query, and query in list instead of tuple"""
        with closing(sqlite3.connect(arcaea_db_manager.userdb_path)) as con:
            with con:
                cur = con.cursor()
                cur.execute("SELECT * FROM arcaea_record", [])
                rec = cur.fetchone()
        assert rec[0] == "fractureray"

    def test__select_joined(self, arcaea_db_manager: arcaea.ArcaeaDbManager):
        res = arcaea_db_manager._select_joined("arcaea_record", user="test")
        assert isinstance(res[0], dict)
        assert res[0]["rating"] == 113

    def test__select(self, arcaea_db_manager: arcaea.ArcaeaDbManager):
        res = arcaea_db_manager._select(
            "arcaea_record", user="test", condition={"pure": 1279}
        )
        assert isinstance(res, list)
        assert res[0].song_id == "fractureray"
        res = arcaea_db_manager._select("arcaea_record")
        assert isinstance(res, list)

    def test__thischart_in_b30(self, arcaea_db_manager: arcaea.ArcaeaDbManager):
        user_id = "test2"
        song_id = "fractureray"
        rating_class = 2
        pure = 1279
        max_pure = 1277
        far = 0
        time = 1
        record = arcaea.playRecord(
            user_id, song_id, rating_class, pure, max_pure, far, time
        )
        assert arcaea_db_manager._thischart_in_b30(record) is None
        arcaea_db_manager._insert("arcaea_best", record)
        record.max_pure = 1276
        assert arcaea_db_manager._thischart_in_b30(record).max_pure == 1277 

    def test__delete(self, arcaea_db_manager: arcaea.ArcaeaDbManager):
        assert arcaea_db_manager._select("arcaea_best", user="test2", condition={"time":1})
        arcaea_db_manager._delete("arcaea_best", user="test2", time=1)
        assert not arcaea_db_manager._select("arcaea_best", user="test2", condition={"time":1})
