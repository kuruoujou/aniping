#!/usr/bin/env python3
"""Aniping package.

Most of aniping's functions are handled within this package. The 6
submodules of this package handle parts relevant to themselves, but
may call other portions of the package.

Here we simply init a nullhandler in the logger.
"""
import logging
try:
    from logging import NullHandler
except ImportError:
    class NullHandler(logging.Handler):
        def emit(self, record):
            pass

logging.getLogger(__name__).addHandler(NullHandler())
