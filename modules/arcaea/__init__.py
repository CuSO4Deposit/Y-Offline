from loguru import logger
from modules.utils import get_config_info, get_project_root, init_project

init_project()
project_root = get_project_root()
log_path = project_root / "log"
log_file = log_path / "arcaea.log"

config_arcaea = get_config_info("Arcaea")
if isinstance(config_arcaea, dict):
    log_level = config_arcaea["loglevel"]
else:
    logger.error("Section [Arcaea] not found in config")
logger.add(log_file, level=log_level, rotation="20 MB")
