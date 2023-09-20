from contextlib import closing
from dataclasses import dataclass, field
from loguru import logger
import sqlite3
from pathlib import Path
from time import sleep
from time import time as current_time
from modules.utils import get_config_info, get_project_root


project_root = get_project_root()
config = get_config_info("YOffline")
config_arcaea = get_config_info("Arcaea")
if not isinstance(config_arcaea, dict):
    logger.error("Section [Arcaea] not found in config")
if isinstance(config, dict):
    logger.error("Section [YOffline] not found in config")
arcsong_path = project_root / config_arcaea["dbpath"]  # used in init of playRecord
userdb_path = project_root / config["dbpath"]
log_level = config_arcaea["loglevel"]


@dataclass
class playRecord(object):
    user_id: str
    song_id: str
    rating_class: int
    pure: int
    max_pure: int
    far: int
    time: int

    lost: int = field(init=False)
    name: str = field(init=False)
    note: int = field(init=False)
    rating: int = field(init=False)
    score: int = field(init=False)
    play_ptt: float = field(init=False)

    @logger.catch
    def __post_init__(self):
        with closing(sqlite3.connect(arcsong_path)) as con:
            with con:
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


def dict_factory(cursor, row):
    fields = [column[0] for column in cursor.description]
    return {key: value for key, value in zip(fields, row)}


class ArcaeaDbManager:
    def __init__(self, arcsong_path: Path, userdb_path: Path):
        self.arcsong_path = arcsong_path
        self.userdb_path = userdb_path

        if not arcsong_path.exists():
            logger.error("arcsong db does not exist.")

        if not userdb_path.exists():
            with closing(sqlite3.connect(userdb_path)) as con:
                with con:
                    with open(
                        get_project_root() / "modules" / "arcaea" / "userdb_setup.sql"
                    ) as f:
                        setup_script = f.read()
                        con.executescript(setup_script)

    def _select_joined(
        self,
        join_table: str,
        user: str | None = None,
        limit: int | None = None,
        order=("[play_ptt]", "DESC"),
    ) -> list[playRecord]:
        join_table_choices = {"arcaea_best", "arcaea_recent", "arcaea_record"}
        if join_table not in join_table_choices:
            logger.error(f"{join_table} not allowed to attach.")
        with closing(sqlite3.connect(self.userdb_path)) as con:
            with con:
                con.row_factory = dict_factory
                cur = con.cursor()
                cur.execute(f"ATTACH '{str(self.arcsong_path)}' AS arcsong")

                query = f"""SELECT * FROM {join_table} LEFT OUTER JOIN arcsong.charts
                    ON {join_table}.[song_id] = arcsong.charts.[song_id] AND {join_table}.[rating_class] = arcsong.charts.[rating_class]
                    """
                if user is not None:
                    query += f"WHERE {join_table}.[user] = ?"
                if order is not None:
                    query += f"ORDER BY {join_table}.{order[0]} {order[1]}"
                if limit is not None:
                    query += f"LIMIT {limit}"

                cur.execute(query, (user,))
                res = cur.fetchall()
                return res

    def _insert_raw(self, table: str, record: playRecord) -> tuple[str, tuple]:
        """return a tuple (query, params) that can be received by cursor.execute()"""
        query = f"""INSERT INTO {table} ([song_id], [rating_class],
                [max_pure], [pure], [far], [play_ptt], [time], [user])
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)"""
        params = (
            record.song_id,
            record.rating_class,
            record.max_pure,
            record.pure,
            record.far,
            record.play_ptt,
            record.time,
            record.user_id,
        )
        return (
            query,
            params,
        )

    def _insert(self, table: str, record: playRecord):
        with closing(sqlite3.connect(self.userdb_path)) as con:
            with con:
                con.execute(*self._insert_raw(table=table, record=record))

    def _select(
        self,
        table: str,
        user: str | None = None,
        limit: int | None = None,
        order=("[play_ptt]", "DESC"),
        condition: dict = {},
    ) -> list[playRecord]:
        """Select from userdb. Condition only supports '=' by now."""
        with closing(sqlite3.connect(self.userdb_path)) as con:
            with con:
                con.row_factory = dict_factory
                cur = con.cursor()
                query = f"SELECT * FROM {table} "
                values = []
                if user is None and condition == {}:
                    pass
                else:
                    if user != None:
                        condition["user"] = user
                    query += "WHERE "
                    for i, (k, v) in enumerate(condition.items()):
                        query += ("" if i == 0 else "AND ") + f"{k} = ? "
                        values.append(v)
                if order != None:
                    query += f"ORDER BY {order[0]} {order[1]} "
                if limit != None:
                    query += f"LIMIT {limit}"
                cur.execute(query, values)
                res = cur.fetchall()
        res = [
            playRecord(
                user_id=i["user"],
                song_id=i["song_id"],
                rating_class=i["rating_class"],
                pure=i["pure"],
                max_pure=i["max_pure"],
                far=i["far"],
                time=i["time"],
            )
            for i in res
        ]
        return res

    def _delete_raw(self, table: str, user: str, time: int) -> tuple[str, tuple]:
        """return a tuple (query, params) that can be received by cursor.execute()"""
        query = f"DELETE FROM {table} WHERE [user] = ? AND [time] = ?"
        params = (
            user,
            time,
        )
        return (
            query,
            params,
        )

    def _delete(self, table: str, user: str, time: int):
        with closing(sqlite3.connect(self.userdb_path)) as con:
            with con:
                con.execute(*self._delete_raw(table=table, user=user, time=time))

    def _transaction(self, queries: list[tuple[str, tuple]]):
        """receive a list of (query, params) and execute in a transaction"""
        with closing(sqlite3.connect(self.userdb_path)) as con:
            with con:
                for query, params in queries:
                    con.execute(query, params)


class ArcaeaManager(ArcaeaDbManager):
    def b30(self, user: str) -> list[playRecord]:
        return self._select("arcaea_best", user=user)

    def r30(self, user: str) -> list[playRecord]:
        return self._select("arcaea_recent", user=user)

    def _thischart_in_db(self, table: str, record: playRecord) -> playRecord | None:
        res = self._select(
            table=table,
            user=record.user_id,
            limit=1,
            condition={
                "[song_id]": record.song_id,
                "[rating_class]": record.rating_class,
            },
        )
        return None if res == [] else res[0]

    def addRecord_best(self, record: playRecord) -> bool:
        b30 = self.b30(user=record.user_id)
        thischart_in_b30 = self._thischart_in_db(table="arcaea_best", record=record)

        # record has play_ptt lower than the lowest one in b30
        if len(b30) == 30 and record.play_ptt <= b30[-1].play_ptt:
            pass
        # this chart is already in b30 and has higher play_ptt
        elif (
            thischart_in_b30 is not None and thischart_in_b30.play_ptt > record.play_ptt
        ):
            pass
        else:
            transaction = []
            # this chart isn't in b30 and b30 is full, record replace the lowest one in b30
            if len(b30) == 30 and thischart_in_b30 is None:
                transaction.append(
                    self._delete_raw("arcaea_best", record.user_id, b30[-1].time)
                )
            # this chart is in b30 and record has higher play_ptt, replace itself
            elif thischart_in_b30 is not None:
                transaction.append(
                    self._delete_raw(
                        "arcaea_best", record.user_id, thischart_in_b30.time
                    )
                )
            # else, this chart isn't in b30 and b30 is not full, simply insert

            transaction.append(self._insert_raw("arcaea_best", record=record))
            self._transaction(transaction)
            return True
        return False

    def _check_highscore(self, record: playRecord) -> bool:
        """True if this record updates high_score"""
        thischart_in_record = self._thischart_in_db(
            table="arcaea_record", record=record
        )
        high_score = 0 if thischart_in_record is None else thischart_in_record.score
        return record.score >= high_score

    def _splitR30(
        self, r30: list[playRecord]
    ) -> tuple[list[playRecord], list[playRecord]]:
        chart_list = []
        r10 = []
        r10_candidate = []
        for r in r30:
            info = (r.song_id, r.rating_class)
            if len(r10) < 10 and info not in chart_list:
                chart_list.append(info)
                r10.append(r)
            else:
                r10_candidate.append(r)
        return r10, r10_candidate

    def r10(self, user: str) -> list[playRecord]:
        return self._splitR30(self.r30(user=user))[0]


## code below is on waitlist


@logger.catch
def addRecord_recent(arcsong_path: Path, userdb_path: Path, record: playRecord) -> bool:
    con = sqlite3.connect(userdb_path)
    cur = con.cursor()
    cur.execute(
        """SELECT [song_id], [rating_class], COUNT(*) FROM recent
        WHERE [user] = ? GROUP BY [song_id], [rating_class]""",
        (record.user_id,),
    )
    chartDict = {(i[0], i[1]): i[2] for i in cur.fetchall()}
    cur.close()
    con.commit()
    cur = con.cursor()
    r30 = getData(arcsong_path, userdb_path, "recent", record.user_id, 30)

    if len(r30) == 30:
        target = []

        # EX / update-high-score protection, this update won't decrease r10.
        if (record.score >= 9800000) or (check_highscore(userdb_path, record)):
            _, r10_candidate = splitR30(r30)
            if (record in r30) and (len(chartDict) <= 10):
                chart_dict = {}
                for i in r10_candidate:
                    info = (i.song_id, i.rating_class)
                    if info not in chart_dict:
                        chart_dict[info] = 1
                    else:
                        chart_dict[info] += 1
                for i in r10_candidate:
                    if chart_dict[(i.song_id, i.rating_class)] > 1:
                        target.append(i)
            else:
                target = r10_candidate

        else:
            if ((record.song_id, record.rating_class) in chartDict) and (
                len(chartDict) <= 10
            ):
                samechart = []
                for r in r30:
                    if (
                        r.song_id == record.song_id
                        and r.rating_class == record.rating_class
                    ):
                        samechart.append(r)
                target = samechart
            else:
                target = r30

        record_to_replace = min(target, key=lambda x: x.time)
        cur.execute(
            """DELETE FROM recent WHERE [time] = ? AND [user] = ?""",
            (
                record_to_replace.time,
                record_to_replace.user_id,
            ),
        )

    cur.execute(
        """INSERT INTO recent ([song_id], [rating_class],
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
    cur.close()
    con.close()
    return True


@logger.catch
def addRecord_record(userdb_path, record: playRecord) -> bool:
    con = sqlite3.connect(userdb_path)
    cur = con.cursor()
    cur.execute(
        """INSERT INTO record ([song_id], [rating_class],
        [max_pure], [pure], [far], [play_ptt], [time], [user])
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
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
    con.close()
    return True


@logger.catch
def addRecord(arcsong_path: Path, userdb_path: Path, record: playRecord) -> bool:
    """True if this record updates b30."""
    addRecord_recent(arcsong_path, userdb_path, record)
    addRecord_record(userdb_path, record)
    update_b30 = addRecord_best(userdb_path, record)
    return update_b30


def _pretty_print(record_list: list[playRecord]) -> str:
    string = ""
    for i in record_list:
        string += f"{i.name[:16]: <16}\t{round(i.play_ptt, 2)}\t{i.time}\n"
    return string


if log_level == "DEBUG":
    con = sqlite3.connect(userdb_path)
    cur = con.cursor()
    cur.execute("""SELECT * FROM record WHERE [user] = 'test'""")
    user = "test"
    if cur.fetchone() is None:
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
        cur.close()
        for i in test_b33:
            pr = playRecord(
                user, i[0], i[1], i[2], i[3], i[4], time=int(current_time())
            )
            addRecord(arcsong_path, userdb_path, pr)
            sleep(1)
    con.commit()
    cur = con.cursor()
    b30 = getData(arcsong_path, userdb_path, "best", user, 50, order=("[time]", "ASC"))
    r30 = getData(
        arcsong_path, userdb_path, "recent", user, 50, order=("[time]", "ASC")
    )
    _, r10c = splitR30(r30)
    # b30 000-, 010-
    # r30 101
    logger.debug(f"[b30 1]\n{_pretty_print(b30[9:13])}\n")
    logger.debug(
        f"[r30 1], expected: es, melody, aiueoon replaces 10, 11, 12 in b30 (0-indexed)\n{_pretty_print(r30[9:13])}\n"
    )
    logger.debug(
        f"[r30 2], expected: es, melody, aiueoon in r10c\n{_pretty_print(r10c[-3:])}\n"
    )

    # b30 100-, replace the lowest
    logger.debug(f"[b30 2] {_pretty_print(b30[-2:])}")
    pr = playRecord(user, "testify", 3, 2219, 2219, 0, time=int(current_time()))
    addRecord(arcsong_path, userdb_path, pr)
    sleep(1)
    b30 = getData(
        arcsong_path, userdb_path, "best", user, 50, order=("[play_ptt]", "DESC")
    )
    r30 = getData(
        arcsong_path, userdb_path, "recent", user, 50, order=("[time]", "ASC")
    )

    logger.debug(
        f"[b30 3] {_pretty_print(b30[-2:])}, expected: the last one of b30-2 is replaced"
    )

    # b30 1011
    logger.debug(f"[b30 4] {_pretty_print(b30[0:1])}")
    pr = playRecord(user, "testify", 3, 2220, 2220, 0, time=int(current_time()))
    addRecord(arcsong_path, userdb_path, pr)
    sleep(1)
    b30 = getData(
        arcsong_path, userdb_path, "best", user, 50, order=("[play_ptt]", "DESC")
    )
    r30 = getData(
        arcsong_path, userdb_path, "recent", user, 50, order=("[time]", "ASC")
    )
    logger.debug(f"[b30 5] {_pretty_print(b30[0:1])}, expected: b30-4 updated")

    # b30 1010
    pr = playRecord(user, "testify", 3, 2218, 2218, 0, time=int(current_time()))
    addRecord(arcsong_path, userdb_path, pr)
    sleep(1)
    b30 = getData(
        arcsong_path, userdb_path, "best", user, 50, order=("[play_ptt]", "DESC")
    )
    logger.debug(f"[b30 6] {_pretty_print(b30[0:1])}, expected: b30-5 not updated")

    # b30 0010
    # r30 011
    r30 = getData(
        arcsong_path, userdb_path, "recent", user, 50, order=("[time]", "ASC")
    )
    logger.debug(f"[r30 3] {_pretty_print(r30[0:1])}")
    pr = playRecord(user, "lapis", 2, 0, 0, 0, time=int(current_time()))
    addRecord(arcsong_path, userdb_path, pr)
    sleep(1)
    b30 = getData(
        arcsong_path, userdb_path, "best", user, 50, order=("[play_ptt]", "DESC")
    )
    r30 = getData(
        arcsong_path, userdb_path, "recent", user, 50, order=("[time]", "ASC")
    )
    logger.debug(f"[b30 7] {_pretty_print(b30[-5:])}, expected: lapis not updated")
    logger.debug(
        f"[r30 4] {_pretty_print(r30[-3:])}, expected: r30-3's last record updated to lapis"
    )

    # r30 110
    for _ in range(30):
        pr = playRecord(user, "testify", 3, 2220, 2220, 0, time=int(current_time()))
        addRecord(arcsong_path, userdb_path, pr)
        sleep(1)
    r30 = getData(
        arcsong_path, userdb_path, "recent", user, 50, order=("[time]", "ASC")
    )
    r10, r10c = splitR30(r30)
    logger.debug(
        f"[r30 5] {_pretty_print(r10c)}, expected: testify with idendical play_ptt"
    )

    # r30 010
    logger.debug(f"[r30 6] {_pretty_print(r10)}")
    pr = playRecord(user, "fractureray", 2, 279, 278, 0, time=int(current_time()))
    addRecord(arcsong_path, userdb_path, pr)
    sleep(1)
    r30 = getData(
        arcsong_path, userdb_path, "recent", user, 30, order=("[time]", "ASC")
    )
    r10, r10c = splitR30(r30)
    logger.debug(
        f"[r30 7] {_pretty_print(r10)}, expected: fractureray replaces itself on r10"
    )

    con.close()
