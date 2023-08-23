# (.+)-Offline

rhythm game score database for self-use

## Arcaea best30 implementation

This implementation may differ from official.

When checking if a record `R` will enter b30 database, and which record it will replace (or simply insert), we take 4 factors for account: 

1. if `R` has higher play_ptt than the lowest one in b30

2. if b30 is not full (i.e. < 30 records in b30)

3. if this chart (i.e. a record with the same song_id and rating_class with `R`) is in b30

4. (if 3 is true), if `R` has higher play_ptt than that.

Truth table:

| 1   | 2   | 3   | 4   | Operation              |
| --- | --- | --- | --- | ---------------------- |
| 0   | 0   | 0   | N/A | - (do nothing)         |
| 0   | 0   | 1   | 0   | -                      |
| 0   | 0   | 1   | 1   | -                      |
| 0   | 1   | 0   | N/A | simply insert into b30 |
| 0   | 1   | 1   | 0   | -                      |
| 0   | 1   | 1   | 1   | update itself          |
| 1   | 0   | 0   | N/A | replace lowest         |
| 1   | 0   | 1   | 0   | -                      |
| 1   | 0   | 1   | 1   | update itself          |
| 1   | 1   | 0   | N/A | replace lowest         |
| 1   | 1   | 1   | 0   | -                      |
| 1   | 1   | 1   | 1   | update itself          |

## Arcaea recent30 implementation

This implementation may differ from official.

Records with the highest 10 play_ptt will be selected into r10. If there are multiple records of one chart, only the highest one takes account. The records in r30 but not in r10 are called r10-candidates.

A record `R` will always enter r30 database, but the record it will replace differs.

- EX / update-high-score protection: when a record reaches EX or higher rank, or it refreshes the highest score of this chart, r10 is guaranteed not to decrease.

- Once reached, there will be >= 10 charts in r30 database. For example,  playing some chart 100 times will result in 21 records of this chart, while the other 9 records (of other charts) remains.

We take 3 factors for account:

1. if `R` reaches EX or higher rank, or it refreshes high score

2. if the chart of `R` is in r30

3. if there are > 10 charts in r30.

Truth table:

| 1   | 2   | 3   | Operation                                                   |
| --- | --- | --- | ----------------------------------------------------------- |
| 0   | 0   | 0   | replace the earliest in r30.                                |
| 0   | 0   | 1   | replace the earliest in r30.                                |
| 0   | 1   | 0   | replace the earliest record of its chart.                   |
| 0   | 1   | 1   | replace the earliest in r30.                                |
| 1   | 0   | 0   | replace the earliest in r10-candidates.                     |
| 1   | 0   | 1   | replace the earliest in r10-candidates.                     |
| 1   | 1   | 0   | replace the earliest record in r10-candidates of its chart. |
| 1   | 1   | 1   | replace the earliest in r10-candidates.                     |

 