# This file should be put in the root dir of the project
from configparser import ConfigParser
from pathlib import Path


def get_project_root() -> Path:
    return Path(__file__).parent.parent.resolve()


def get_config_info(query: str | None = None):
    parser = ConfigParser()
    parser.read("./config.ini")
    sections = parser.sections()
    if query is None:
        return sections
    if query in sections:
        return dict(parser[query])
    else:
        return None
