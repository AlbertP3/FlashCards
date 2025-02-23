import os
import sys
import signal
import logging
from logging.handlers import RotatingFileHandler
import matplotlib
from types import FrameType

CWD = os.path.dirname(os.path.abspath(__file__))


def configure_logging(log_level, plt_log_level="error"):
    logging.basicConfig(
        format="%(asctime)s.%(msecs)03d [%(name)s] %(levelname)s %(message)s <%(filename)s(%(lineno)d)>",
        datefmt="%Y-%m-%dT%H:%M:%S",
        level=log_level,
        handlers=(
            RotatingFileHandler(
                filename=os.path.realpath(f"{CWD}/../fcs.log"),
                mode="a",
                maxBytes=512**2,
                backupCount=1,
            ),
        ),
    )
    LOGGER = logging.getLogger("FCS")
    sys.stderr.write = LOGGER.critical
    matplotlib.set_loglevel(plt_log_level)


try:
    import cfg
except Exception as e:
    configure_logging("DEBUG", "DEBUG")
    log = logging.getLogger("FCS")
    log.critical(e, exc_info=True)
    sys.exit(1)

configure_logging(cfg.config["log_level"])
log = logging.getLogger("FCS")
sys.stdout.write = lambda msg: log.debug(msg, stacklevel=2) if msg != "\n" else None
sys.stderr.write = lambda msg: log.error(msg, stacklevel=2) if msg != "\n" else None

log.debug(f"Launching Flashcards {cfg.config['version']}")

from main_window_gui import MainWindowGUI

mw = MainWindowGUI()


def handle_termination_signal(signum, frame: FrameType):
    mw.closeEvent(None)
    log.critical(f"Application terminated with signal {signal.Signals(signum).name}")
    sys.exit(0)


signal.signal(signal.SIGTERM, handle_termination_signal)
signal.signal(signal.SIGINT, handle_termination_signal)

mw.launch_app()

log.debug("Application shutdown")
