from modules.arcaea import utils as arcaea
from loguru import logger
import pytest
from modules.utils import get_project_root


@pytest.fixture
def arcaea_db_manager():
    root = get_project_root()
    arcsong_path = root / "database" / "ArcaeaSongDatabase" / "arcsong.db"
    userdb_path = root / "database" / "yoffline.db"
    return arcaea.ArcaeaDbManager(arcsong_path=arcsong_path, userdb_path=userdb_path)


def test_PlayRecord(arcaea_db_manager):
    from time import time as current_time

    user_id = "test"
    song_id = "fractureray"
    rating_class = 2
    pure = 1279
    max_pure = 1277
    far = 0
    time = 1

    record = arcaea.playRecord(
        user_id, song_id, rating_class, pure, max_pure, far, time, arcaea_db_manager
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
        arcaea_db_manager,
    )
    assert record.score == 9997367
    assert str(record.time)[0] == "1"
