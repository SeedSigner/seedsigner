import sys
import logging
from logging.handlers import RotatingFileHandler


def configure_logging(log_file="debug.log"):

    # Configure logging handlers for different streams

    logger = logging.getLogger()
    logger.setLevel(logging.DEBUG)

    class UpperThresholdFilter(logging.Filter):
        def __init__(self, threshold, *args, **kwargs):
            self._threshold = threshold
            super(UpperThresholdFilter, self).__init__(*args, **kwargs)

        def filter(self, rec):
            return rec.levelno <= self._threshold

    logfmt = "{}[%(asctime)s|%(levelname).3s]{} %(message)s"

    stdouthandler = logging.StreamHandler(sys.stdout)
    stdouthandler.setLevel(logging.DEBUG)
    stdouthandler.addFilter(UpperThresholdFilter(logging.INFO))
    logger.addHandler(stdouthandler)

    stderrhandler = logging.StreamHandler(sys.stderr)
    stderrhandler.setLevel(logging.WARNING)
    logger.addHandler(stderrhandler)

    filehandler = RotatingFileHandler(log_file, maxBytes=1024 * 1024 * 100, backupCount=5)
    filehandler.setLevel(logging.DEBUG)
    filehandler.setFormatter(logging.Formatter(logfmt.format("", "")))
    logger.addHandler(filehandler)
