from dataclasses import dataclass, field
from loguru import logger
import sqlite3
from time import gmtime, strftime
from time import time as current_time
from __init__ import db_path, log_level



@dataclass
class playRecord(object):
    
    user_id: str
    song_id: str
    rating_class: int
    pure: int
    max_pure: int
    far: int

    time: int = int(current_time())
    lost: int = field(init=False)
    note: int = field(init=False)
    rating: int = field(init=False)
    score: int = field(init=False)
    play_ptt: float = field(init=False)


    @logger.catch
    def __post_init__(self):
        con = sqlite3.connect(db_path / "arcsong.db")
        cur = con.cursor()
        cur.execute(
            "SELECT [rating], [note] FROM charts WHERE [song_id] = ? AND [rating_class] = ?",
            (
            self.song_id,
            self.rating_class,
            ),
        )
        self.rating, self.note = cur.fetchone()
        con.close()

        # self.time = int(current_time())
        self.lost = self.note - self.pure - self.far
        self.score = self.calc_score()
        self.play_ptt = self.calc_ptt()


    def calc_score(self) -> int:
        purePerNote = 10000000 / self.note
        return int(purePerNote * (self.pure + self.far / 2) + self.max_pure)


    def calc_ptt(self) -> float:
        if self.score > 10000000:
            return self.rating / 10 + 2
        elif self.score >= 9800000:
            return self.rating / 10 + 1 + (self.score - 9800000) / 200000
        else:
            return max(0, self.rating / 10 + (self.score - 9500000) / 300000)


if log_level == "DEBUG":
    user_id = "test"
    song_id = "fractureray"
    rating_class = 2
    pure = 1279
    max_pure = 1277
    far = 0
    time = 1

    record = playRecord(user_id, song_id, rating_class, pure, max_pure, far, time=time)
    assert record.score == 10001277
    assert record.play_ptt == 13.3

    pure = 1278
    far = 1
    record = playRecord(user_id, song_id, rating_class, pure, max_pure, far, time=time)
    assert record.score == 9997367
    logger.debug(record.play_ptt)
