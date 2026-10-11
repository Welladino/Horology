"""Argument-free JSON log output shared across Horology services."""
import logging
import sys

logger = logging.getLogger('horology.operations')
if not logger.handlers:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(logging.Formatter('%(message)s'))
    logger.addHandler(handler)
logger.setLevel(logging.INFO)
logger.propagate = False
