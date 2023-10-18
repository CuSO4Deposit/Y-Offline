BEGIN;

CREATE TABLE [yoffline_user](
[username] VARCHAR(32) PRIMARY KEY,
[password] CHAR(64),
[bio] TEXT);

CREATE TABLE [arcaea_record](
        [song_id] TEXT NOT NULL,
        [rating_class] INTEGER NOT NULL DEFAULT 2,
        [pure] INTEGER NOT NULL,
        [max_pure] INTEGER NOT NULL,
        [far] INTEGER NOT NULL, 
        [play_ptt] FLOAT NOT NULL,
        [time] INTEGER NOT NULL,
        [user] TEXT NOT NULL,
        PRIMARY KEY([time], [user]));

CREATE TABLE [arcaea_best](
        [song_id] TEXT NOT NULL,
        [rating_class] INTEGER NOT NULL DEFAULT 2,
        [pure] INTEGER NOT NULL,
        [max_pure] INTEGER NOT NULL,
        [far] INTEGER NOT NULL,
        [play_ptt] REAL NOT NULL,
        [time] INTEGER NOT NULL,
        [user] TEXT NOT NULL,
        PRIMARY KEY([time], [user]));

CREATE TABLE [arcaea_recent](
        [song_id] TEXT NOT NULL,
        [rating_class] INTEGER NOT NULL DEFAULT 2,
        [pure] INTEGER NOT NULL,
        [max_pure] INTEGER NOT NULL,
        [far] INTEGER NOT NULL,
        [play_ptt] REAL NOT NULL,
        [time] INTEGER NOT NULL,
        [user] TEXT NOT NULL,
        PRIMARY KEY([time], [user]));

CREATE TABLE [arcaea_deleted_best](
        [song_id] TEXT NOT NULL,
        [rating_class] INTEGER NOT NULL DEFAULT 2,
        [pure] INTEGER NOT NULL,
        [max_pure] INTEGER NOT NULL,
        [far] INTEGER NOT NULL,
        [play_ptt] REAL NOT NULL,
        [time] INTEGER NOT NULL,
        [user] TEXT NOT NULL,
        [deleted_time] INTEGER NOT NULL,
        PRIMARY KEY([time], [user]));

CREATE TABLE [arcaea_deleted_recent](
        [song_id] TEXT NOT NULL,
        [rating_class] INTEGER NOT NULL DEFAULT 2,
        [pure] INTEGER NOT NULL,
        [max_pure] INTEGER NOT NULL,
        [far] INTEGER NOT NULL,
        [play_ptt] REAL NOT NULL,
        [time] INTEGER NOT NULL,
        [user] TEXT NOT NULL,
        [deleted_time] INTEGER NOT NULL,
        PRIMARY KEY([time], [user]));

CREATE TRIGGER backup_best BEFORE DELETE
ON arcaea_best
    BEGIN
        INSERT INTO arcaea_deleted_best(
            [song_id], [rating_class], [pure], [max_pure],
            [far], [play_ptt], [time], [user], [deleted_time]
        )
        VALUES(
            OLD.[song_id], OLD.[rating_class], OLD.[pure], OLD.[max_pure],
            OLD.[far], OLD.[play_ptt], OLD.[time], OLD.[user], datetime('now')
        );
    END;

CREATE TRIGGER backup_recent BEFORE DELETE
ON arcaea_recent
    BEGIN
        INSERT INTO arcaea_deleted_recent(
            [song_id], [rating_class], [pure], [max_pure],
            [far], [play_ptt], [time], [user], [deleted_time]
        )
        VALUES(
            OLD.[song_id], OLD.[rating_class], OLD.[pure], OLD.[max_pure],
            OLD.[far], OLD.[play_ptt], OLD.[time], OLD.[user], datetime('now')
        );
    END;

COMMIT;
