from contextlib import closing
from dataclasses import dataclass, field, InitVar
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
        self, join_table: str, user: str, limit: int, order=("[play_ptt]", "DESC")
    ) -> playRecord:
        # TODO
        pass


## code below is on waitlist


class ArcaeaManager:
    def __init__(self, arcsong_path: Path, userdb_path: Path):
        self.arcaea_db_manager = ArcaeaDbManager(
            arcsong_path=arcsong_path, userdb_path=userdb_path
        )

    @logger.catch
    def _getData(
        self,
        table: str,
        user: str,
        limit: int,
        order=("[play_ptt]", "DESC"),
    ) -> list[playRecord]:
        arcsong_path = self.arcaea_db_manager.arcsong_path
        userdb_path = self.arcaea_db_manager.userdb_path
        arcsong_path_str = str(arcsong_path)
        con = sqlite3.connect(userdb_path)
        cur = con.cursor()
        cur.execute(f"ATTACH '{arcsong_path_str}' AS arcsong")

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
        con.commit()
        con.close()
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
                time=i[9],
                arcaea_db_manager=self.arcaea_db_manager,
            )
            for i in res
        ]
        return res


def addRecord_best(userdb_path: Path, record: playRecord) -> bool:
    con = sqlite3.connect(userdb_path)
    cur = con.cursor()
    cur.execute(
        """SELECT [play_ptt], [time] FROM best WHERE [user] = ?
        ORDER BY [play_ptt] ASC""",
        (record.user_id,),
    )
    b30 = cur.fetchall()
    con.commit()
    cur.close()
    cur = con.cursor()
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
    cur.close()
    con.commit()
    cur = con.cursor()

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
        con.close()
        return True
    con.close()
    return False


@logger.catch
def check_highscore(userdb_path: Path, record: playRecord) -> bool:
    """True if this record updates high_score"""
    con = sqlite3.connect(userdb_path)
    cur = con.cursor()
    cur.execute(
        """SELECT [play_ptt] FROM record
        WHERE [user] = ? and [song_id] = ? and [rating_class] = ?
        ORDER BY [play_ptt] DESC LIMIT 1""",
        (
            record.user_id,
            record.song_id,
            record.rating_class,
        ),
    )
    former = cur.fetchone()
    con.commit()
    con.close()
    if former is None:
        former = (0,)
    return record.play_ptt >= former[0]


@logger.catch
def splitR30(r30: list[playRecord]):
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
