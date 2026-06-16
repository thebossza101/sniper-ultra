"""
SNIPER ULTRA — Logger (ASCII-safe untuk Windows cp1252)
"""
import logging
import sys
from datetime import datetime

LOG_LEVELS = {"DEBUG": 10, "INFO": 20, "WARN": 30, "ERROR": 40}

class AsciiFilter(logging.Filter):
    """Filter Unicode chars that crash Windows cp1252 console"""
    def filter(self, record):
        if isinstance(record.msg, str):
            record.msg = self._ascii_safe(record.msg)
        if record.args:
            record.args = tuple(
                self._ascii_safe(a) if isinstance(a, str) else a
                for a in record.args
            )
        return True

    @staticmethod
    def _ascii_safe(text):
        replacements = {
            '\u2192': '->', '\u2191': '^^', '\u2193': 'vv',
            '\u2705': '[OK]', '\u274c': '[X]', '\u26a0\ufe0f': '[!]',
            '\u2757': '[!]', '\u2b06\ufe0f': '[UP]', '\u2b07\ufe0f': '[DN]',
            '\U0001f534': '[RED]', '\U0001f7e2': '[GRN]',
            '\U0001f535': '[BLU]', '\U0001f4a7': '[DRP]',
            '\u2795': '[+]', '\u2796': '[-]',
            '\U0001f4a2': '[BOOM]', '\u26a1': '[ZAP]',
            '\U0001f525': '[FIRE]', '\U0001f4a9': '[POOP]',
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        # Remove remaining non-ASCII
        return text.encode('ascii', 'replace').decode('ascii')

def setup_logger(name="SNIPER", level="INFO"):
    logger = logging.getLogger(name)
    logger.setLevel(LOG_LEVELS.get(level.upper(), 20))
    logger.handlers.clear()

    fmt = logging.Formatter(
        '%(asctime)s|%(levelname)s|%(message)s',
        datefmt='%H:%M:%S'
    )

    # Console handler
    ch = logging.StreamHandler(sys.stdout)
    ch.setFormatter(fmt)
    ch.addFilter(AsciiFilter())
    logger.addHandler(ch)

    # File handler (no filter needed)
    fh = logging.FileHandler(f"sniper_{datetime.now().strftime('%Y%m%d')}.log", encoding='ascii')
    fh.setFormatter(fmt)
    logger.addHandler(fh)

    return logger

log = setup_logger()
