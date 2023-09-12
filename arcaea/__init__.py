print(__name__)
from loguru import logger
from utils import get_config_info, get_project_root

project_root = get_project_root()
log_path = project_root / "log"
log_path.mkdir(exist_ok=True)
log_file = log_path / "Arcaea.log"
log_file.touch(exist_ok=True)

config_arcaea = get_config_info("Arcaea")
if isinstance(config_arcaea, dict):
    log_level = config_arcaea["loglevel"]
    arcsong_path = project_root / config_arcaea["dbpath"]
    userdb_path = project_root / config_arcaea["userdbpath"]
else:
    logger.error("Section [Arcaea] not found in config")
logger.add(log_file, level=log_level, rotation="20 MB")
