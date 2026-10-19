import logging
from logging.handlers import RotatingFileHandler
from pathlib import Path


def configure_logging() -> None:
    """Configure a rotating local log file once."""
    logger = logging.getLogger("payment_reconciliation")

    if logger.handlers:
        return

    log_directory = Path(__file__).resolve().parent.parent / "data" / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        log_directory / "application.log",
        maxBytes=1_000_000,
        backupCount=2,
        encoding="utf-8",
    )
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)s %(name)s %(message)s"
        )
    )

    logger.setLevel(logging.INFO)
    logger.addHandler(handler)
    logger.propagate = False
