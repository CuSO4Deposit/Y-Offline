# MUG-scoredb

for self-use

## Arcaea best30 implementation

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