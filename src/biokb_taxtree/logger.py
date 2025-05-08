import logging
import logging.config
import os
from typing import Optional

from yaml import safe_load


def setup_logging(path: Optional[str] = None, default_level=logging.DEBUG):
    """Setup logging configuration

    If no path is set, default logger configuration is used.

    Args:
        path (Optional[str], optional): Path to logging config yaml file. Defaults to None.
        default_level (_type_, optional): Default logging level. Defaults to logging.WARNING.
    """
    if not path:
        path = os.path.join(os.path.dirname(__file__), "logging_config.yaml")
    if os.path.exists(path):
        with open(path, "rt") as f:
            config = safe_load(f.read())
        logging.config.dictConfig(config)
    else:
        logging.basicConfig(level=default_level)
