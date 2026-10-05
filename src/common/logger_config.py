import logging
import sys
from typing import ClassVar


class ColorFormatter(logging.Formatter):
    WHITE = "\033[37m"
    YELLOW = "\033[33m"
    RED = "\033[31m"
    DARK_RED = "\033[31;1m"
    RESET = "\033[0m"

    FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    FORMATS: ClassVar[dict[int, str]] = {
        logging.DEBUG: WHITE + FORMAT + RESET,
        logging.INFO: WHITE + FORMAT + RESET,
        logging.WARNING: YELLOW + FORMAT + RESET,
        logging.ERROR: RED + FORMAT + RESET,
        logging.CRITICAL: DARK_RED + FORMAT + RESET
    }

    def format(self, record):
        log_fmt = self.FORMATS.get(record.levelno)
        formatter = logging.Formatter(log_fmt)
        return formatter.format(record)


def setup_logger():
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.INFO)

    if root_logger.hasHandlers():
        root_logger.handlers.clear()

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(ColorFormatter())

    root_logger.addHandler(console_handler)


setup_logger()
