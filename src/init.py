import os
import sys
import json
import signal
import logging
import builtins
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


def handle_termination_signal(signum, frame: FrameType):
    utils.config.save()
    log.critical(f"Application terminated with signal {signal.Signals(signum).name}")
    sys.exit(0)


try:
    if not os.path.exists("./src/res/config.json"):
        json.dump(
            json.load(open("./src/res/config-default.json", "r")),
            open("./src/res/config.json", "w"),
            indent=4,
            ensure_ascii=False,
        )
    import utils

    configure_logging(utils.config["log_level"])
    signal.signal(signal.SIGTERM, handle_termination_signal)
    signal.signal(signal.SIGINT, handle_termination_signal)
except Exception as e:
    configure_logging("DEBUG", "DEBUG")
    log = logging.getLogger("FCS")
    log.critical(e, exc_info=True)
    sys.exit(1)

log = logging.getLogger("FCS")
builtins.print = lambda *args, **kwargs: log.debug(' '.join(map(str, args)))
log.debug(f"*** Flashcards {utils.config['version']} ***")

from main_window_gui import main_window_gui

mw = main_window_gui()
mw.launch_app()

log.debug("*** Application shutdown ***")
