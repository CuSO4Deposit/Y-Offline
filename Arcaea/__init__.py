from loguru import logger
from pathlib import Path


Path("./log/").mkdir(exist_ok=True)
log_file = Path("./log/Arcaea.log")
log_file.touch(exist_ok=True)

log_level = "DEBUG"
logger.add(log_file, level=log_level, rotation="20 MB")

db_path = Path("./Arcaea/ArcaeaSongDatabase/")
