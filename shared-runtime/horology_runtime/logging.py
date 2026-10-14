"""Argument-free JSON log output shared across Horology services."""
import json
import logging
import sys

logger = logging.getLogger('horology.operations')
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False


class JsonLines(logging.Formatter):
    """One JSON object per line; Cloud Logging reads `severity` and `message`, so warnings can be
    filtered by severity and by logger in Log Analytics. Tracebacks are left out: they can carry data."""

    def format(self, record):
        return json.dumps({'severity': record.levelname, 'logger': record.name, 'message': record.getMessage()},
                          separators=(',', ':'))


def use_json_lines(level):
    """Send every stdlib logger (except the operations logger above, already JSON) to stdout as JsonLines."""
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonLines())
    logging.basicConfig(level=level, handlers=[handler], force=True)
