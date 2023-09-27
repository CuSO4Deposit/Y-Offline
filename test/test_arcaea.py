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
def arcaea_manager():
    project_root = get_project_root()
    config = get_config_info("YOffline")
    config_arcaea = get_config_info("Arcaea")
    if not isinstance(config_arcaea, dict):
        logger.error("Section [Arcaea] not found in config")
    if not isinstance(config, dict):
        logger.error("Section [YOffline] not found in config")
    arcsong_path = project_root / config_arcaea["dbpath"]
    userdb_path = Path(__file__).parent / "user.db"
    yield arcaea.ArcaeaManager(arcsong_path=arcsong_path, userdb_path=userdb_path)
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
    def test__insert(self, arcaea_manager: arcaea.ArcaeaManager):
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
        arcaea_manager._insert(table="arcaea_record", record=record)

    def test_sqlite_empty_query(self, arcaea_manager: arcaea.ArcaeaManager):
        """test if sqlite supports empty query, and query in list instead of tuple"""
        with closing(sqlite3.connect(arcaea_manager.userdb_path)) as con:
            with con:
                cur = con.cursor()
                cur.execute("SELECT * FROM arcaea_record", [])
                rec = cur.fetchone()
        assert rec[0] == "fractureray"

    def test__select_joined(self, arcaea_manager: arcaea.ArcaeaManager):
        res = arcaea_manager._select_joined("arcaea_record", user="test")
        assert isinstance(res[0], dict)
        assert res[0]["rating"] == 113

    def test__select(self, arcaea_manager: arcaea.ArcaeaManager):
        res = arcaea_manager._select(
            "arcaea_record", user="test", condition={"pure": 1279}
        )
        assert isinstance(res, list)
        assert res[0].song_id == "fractureray"
        res = arcaea_manager._select("arcaea_record")
        assert isinstance(res, list)

    def test__thischart_in_db(self, arcaea_manager: arcaea.ArcaeaManager):
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
        assert arcaea_manager._thischart_in_db("arcaea_best", record) is None
        arcaea_manager._insert("arcaea_best", record)
        max_pure = 1276
        record = arcaea.playRecord(
            user_id, song_id, rating_class, pure, max_pure, far, time
        )
        assert arcaea_manager._thischart_in_db("arcaea_best", record).max_pure == 1277

    def test__delete(self, arcaea_manager: arcaea.ArcaeaManager):
        assert arcaea_manager._select(
            "arcaea_best", user="test2", condition={"time": 1}
        )
        arcaea_manager._delete("arcaea_best", user="test2", time=1)
        assert not arcaea_manager._select(
            "arcaea_best", user="test2", condition={"time": 1}
        )
        assert arcaea_manager._select("arcaea_deleted_best", user="test2")

    def test__transation(self, arcaea_manager: arcaea.ArcaeaManager):
        user_id = "test2"
        song_id = "fractureray"
        rating_class = 2
        pure = 1278
        max_pure = 1277
        far = 1
        time = 1
        record = arcaea.playRecord(
            user_id, song_id, rating_class, pure, max_pure, far, time
        )

        arcaea_manager._transaction(
            [
                arcaea_manager._insert_raw("arcaea_record", record),
                arcaea_manager._delete_raw("arcaea_record", user=user_id, time=time),
            ]
        )
        assert arcaea_manager._select("arcaea_record", user=user_id) == []

        try:
            arcaea_manager._transaction(
                [
                    arcaea_manager._insert_raw("arcaea_record", record),
                    ("not_valid_table", ()),
                ]
            )
        except:
            pass
        assert arcaea_manager._select("arcaea_record", user=user_id) == []


def _pretty_print(record_list: list[arcaea.playRecord]) -> str:
    string = ""
    for i in record_list:
        string += f"{i.name[:16]: <16}\t{round(i.play_ptt, 2)}\t{i.time}\n"
    return string


class Test_ArcManager:
    def test__check_highscore(self, arcaea_manager: arcaea.ArcaeaManager):
        user_id = "test"
        song_id = "fractureray"
        rating_class = 2
        pure = 1279
        max_pure = 1278
        far = 0
        time = 2

        record = arcaea.playRecord(
            user_id, song_id, rating_class, pure, max_pure, far, time
        )
        assert arcaea_manager._check_highscore(record=record)

        pure = 1278
        record = arcaea.playRecord(
            user_id, song_id, rating_class, pure, max_pure, far, time
        )
        assert arcaea_manager._check_highscore(record=record) == False

        arcaea_manager._delete("arcaea_record", user=user_id, time=1)

    def test_addRecord(self, arcaea_manager: arcaea.ArcaeaManager):
        user = "test3"
        test_b33 = [
            ["grievouslady", 2, 1370, 1189, 52],
            ["lastcelebration", 2, 1434, 1293, 32],
            ["valhallazero", 2, 1142, 1012, 26],
            ["battlenoone", 2, 1037, 936, 5],
            ["cyaegha", 2, 1317, 1121, 36],
            ["fractureray", 2, 1203, 1052, 43],
            ["alexandrite", 2, 1024, 884, 13, 3],
            ["akinokagerou", 2, 1068, 951, 6],
            ["singularity", 2, 1062, 902, 30],
            ["memoryforest", 2, 968, 879, 9],
            ["halcyon", 2, 1181, 1050, 28],
            ["sheriruth", 2, 1127, 953, 20],
            ["sulfur", 2, 1038, 951, 5],
            ["worldfragments", 2, 1372, 12, 3],
            ["dreadnought", 2, 1089, 942, 9],
            ["amygdata", 2, 1187, 1105, 11, 1],
            ["themessage", 2, 984, 911, 5],
            ["corruption", 2, 1279, 1206, 8],
            ["metallicpunisher", 2, 1206, 1084, 20],
            ["trappola", 2, 1023, 920, 17],
            ["tothemilkyway", 2, 1346, 1190, 28],
            ["heavensdoor", 2, 1084, 977, 11],
            ["gimmick", 2, 729, 669, 4],
            ["fractureray", 1, 1336, 1269, 6],
            ["dataerror", 2, 949, 880, 5],
            ["blrink", 2, 1001, 868, 12],
            ["supernova", 2, 1109, 979, 10],
            ["yozakurafubuki", 2, 927, 815, 4],
            ["lapis", 2, 916, 827, 4],
            ["eveninginscarlet", 2, 915, 829, 6],
            ["etherstrike", 2, 1133, 989, 26],
            ["melodyoflove", 2, 920, 819, 10],
            ["aiueoon", 2, 984, 889, 5],
        ]
        for idx, i in enumerate(test_b33):
            pr = arcaea.playRecord(
                user, i[0], i[1], i[2], i[3], i[4], time=idx,
            )
            arcaea_manager.addRecord(pr) 

        # b30 000-, 010-
        # r30 101
        # after 33 records inserted, b30 only has 30 records.
        b30 = arcaea_manager.b30("test3")
        assert len(b30) == 30
        b30_songid_list = (i.song_id for i in b30)
        # b31, b32, b33 not in b30
        assert "etherstrike" not in b30_songid_list
        assert "melodyoflove" not in b30_songid_list
        assert "aiueoon" not in b30_songid_list
        r10, r10c = arcaea_manager._splitR30(arcaea_manager.r30(user=user))
        r10_songid_list = {i.song_id for i in r10}
        r10c_songid_list = {i.song_id for i in r10c}
        print(r10c_songid_list)
        # no protection, it flashes out "grievouslady"
        assert "etherstrike" in r10_songid_list
        assert "grievouslady" not in r10_songid_list
        # EX protection, it tries to flash out "lastcelebration" but fails.
        # Then it will flash out earliest in r10c
        assert "melodyoflove" in r10c_songid_list
        assert "aiueoon" in r10c_songid_list

        # b30 100-, replace the lowest
        pr = arcaea.playRecord(user, "testify", 3, 2219, 2219, 0, time=34) 
        arcaea_manager.addRecord(pr)
        b30 = arcaea_manager.b30(user=user)
        b30_songid_list = {i.song_id for i in b30}
        # the record with lowest ptt in b30 is replaed
        assert "eveninginscarlet" not in b30_songid_list
        assert "testify" in b30_songid_list
    
        # b30 1011
        pr = arcaea.playRecord(user, "testify", 3, 2220, 2220, 0, time=35)
        arcaea_manager.addRecord(pr)
        b30 = arcaea_manager.b30(user=user)
        # same chart, updates itself
        assert b30[0].pure == 2220

        # b30 1010
        pr = arcaea.playRecord(user, "testify", 3, 2218, 2218, 0, time=36)
        arcaea_manager.addRecord(pr)
        b30 = arcaea_manager.b30(user=user)
        # same chart, but did not update highscore, do not update b30
        assert b30[0].pure != 2218

        # b30 0010
        # r30 011
        r30 = arcaea_manager.r30(user=user)
        former_r30_latest = r30[0]
        pr = arcaea.playRecord(user, "lapis", 2, 0, 0, 0, time=37)
        arcaea_manager.addRecord(pr)
        b30 = arcaea_manager.b30(user=user)
        r30 = arcaea_manager.r30(user=user)
        # the latest one of r30 is updated
        assert r30[0] != former_r30_latest
        # this record won;t update b30
        lapis_in_b30 = {i for i in b30 if i.song_id == "lapis"}.pop()
        assert lapis_in_b30.pure != 0
        
        # r30 110
        for i in range(30):
            pr = arcaea.playRecord(user, "testify", 3, 2220, 2220, 0, time=38 + i)
            arcaea_manager.addRecord(pr)
        r30 = arcaea_manager.r30(user=user)
        _, r10c = arcaea_manager._splitR30(r30)
        score_in_r10c = {i.score for i in r10c}
        # all records in r10c has same score.
        assert len(score_in_r10c) == 1

        # r30 010
        fractureray_in_former_r30 = {i for i in r30 if i.song_id == "fractureray"}.pop()
        pr = playRecord(user, "fractureray", 2, 279, 278, 0, time=68)
        arcaea_manager.addRecord(pr)
        fractureray_in_current_r30 = {i for i in r30 if i.song_id == "fractureray"}.pop()
        assert fractureray_in_current_r30 != fractureray_in_former_r30
