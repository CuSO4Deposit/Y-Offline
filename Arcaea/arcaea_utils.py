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
    name: str = field(init=False)
    note: int = field(init=False)
    rating: int = field(init=False)
    score: int = field(init=False)
    play_ptt: float = field(init=False)

    @logger.catch
    def __post_init__(self):
        con = sqlite3.connect(db_path / "arcsong.db")
        cur = con.cursor()
        cur.execute(
            "SELECT [rating], [note], [name_jp], [name_en] FROM charts WHERE [song_id] = ? AND [rating_class] = ?",
            (
                self.song_id,
                self.rating_class,
            ),
        )
        self.rating, self.note, name_jp, name_en = cur.fetchone()
        self.name = name_en if name_jp == "" else name_jp
        con.close()

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
    record = playRecord(user_id, song_id, rating_class, pure, max_pure, far)
    assert record.score == 9997367
    logger.debug(f"[playRecord] {record.time}")


@logger.catch
def getData(
    table: str, user: str, limit: int, order=("[play_ptt]", "DESC")
) -> list[playRecord]:
    arcsong_path = str((db_path / "arcsong.db").resolve())
    con = sqlite3.connect(db_path / "user.db")
    cur = con.cursor()
    cur.execute(f"ATTACH '{arcsong_path}' AS arcsong")

    query = f"""SELECT arcsong.charts.[name_jp], arcsong.charts.[name_en],
        {table}.[rating_class], arcsong.charts.[note], {table}.[pure],
        {table}.[max_pure], {table}.[far], arcsong.charts.[rating],
        {table}.[play_ptt], {table}.[time], arcsong.charts.[song_id]
        FROM {table} LEFT OUTER JOIN arcsong.charts
        ON {table}.[song_id] = arcsong.charts.[song_id] AND {table}.[rating_class] = arcsong.charts.[rating_class]
        WHERE {table}.[user] = ? ORDER BY {table}.{order[0]} {order[1]}
        LIMIT {limit}
        """

    cur.execute(query, (user,))
    res = cur.fetchall()
    # [name_jp]     [name_en]   [rating_class]  [note]      [pure]
    # [max_pure]    [far]       [rating]        [play_ptt]  [time]
    # [song_id]

    if res == []:
        logger.warning(f"No result for this query, user: {user}, table: {table}.")
        return []

    res = [
        playRecord(
            user_id=user,
            song_id=i[10],
            rating_class=i[2],
            pure=i[4],
            max_pure=i[5],
            far=i[6],
            time=gmtime(i[9]),
        )
        for i in res
    ]
    logger.success(f"[getData] success. user: {user}, table: {table}")
    return res


if log_level == "DEBUG":
    data = getData("best", "temp", 30)
    logger.debug(f"[getData] {data}")
    # to be continued with addRecord()


def addRecord_best(record: playRecord) -> bool:
    con = sqlite3.connect(db_path / "user.db")
    cur = con.cursor()
    cur.execute(
        """SELECT [play_ptt], [time] FROM best WHERE [user] = ?
        ORDER BY [play_ptt] ASC""",
        (record.user_id,),
    )
    b30 = cur.fetchall()
    cur.execute(
        """SELECT [play_ptt], [time], [user] FROM best 
        WHERE [song_id] = ? AND [rating_class] = ? AND [user] = ?""",
        (
            record.song_id,
            record.rating_class,
            record.user_id,
        ),
    )
    thisChart = cur.fetchone()

    # record has play_ptt lower than the lowest one in b30
    if len(b30) == 30 and record.play_ptt <= b30[0][0]:
        pass
    # this chart is already in b30 and has higher play_ptt
    elif thisChart is not None and thisChart[0] > record.play_ptt:
        pass
    else:
        # this chart isn't in b30 and b30 is full, record replace the lowest one in b30
        if len(b30) == 30 and thisChart is None:
            cur.execute(
                "DELETE FROM best WHERE [user] = ? AND [time] = ?",
                (
                    record.user_id,
                    b30[0][1],
                ),
            )
        # this chart is in b30 and record has higher play_ptt, replace itself
        elif thisChart is not None:
            cur.execute(
                "DELETE FROM best WHERE [user] = ? AND [time] = ?",
                (
                    record.user_id,
                    thisChart[1],
                ),
            )
        # else, this chart isn't in b30 and b30 is not full, simply insert

        cur.execute(
            """INSERT INTO best ([song_id], [rating_class],
            [max_pure], [pure], [far], [play_ptt], [time], [user])
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
            (
                record.song_id,
                record.rating_class,
                record.max_pure,
                record.pure,
                record.far,
                record.play_ptt,
                record.time,
                record.user_id,
            ),
        )
        con.commit()
        return True
    return False


# test TODO


@logger.catch
def addRecord_recent(record: playRecord) -> bool:
    # TODO
    pass


@logger.catch
def addRecord_record(record: playRecord) -> bool:
    con = sqlite3.connect(db_path / "user.db")
    cur = con.cursor()
    cur.execute(
        """INSERT INTO record ([song_id], [rating_class],
        [max_pure], [pure], [far], [time], [user])
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            record.song_id,
            record.rating_class,
            record.max_pure,
            record.pure,
            record.far,
            record.time,
            record.user_id,
        ),
    )
    con.commit()
    return True


def addRecord(record: playRecord) -> None:
    addRecord_record(record)
    addRecord_best(record)
    addRecord_recent(record)
