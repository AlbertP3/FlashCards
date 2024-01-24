import os
import sys
import logging
import matplotlib

CWD = os.path.dirname(os.path.abspath(__file__))


def configure_logging(log_level, plt_log_level="error"):
    logging.basicConfig(
        filename=os.path.realpath(f"{CWD}/../fcs.log"),
        filemode="a",
        format="%(asctime)s.%(msecs)03d [%(name)s] %(levelname)s %(message)s <%(filename)s(%(lineno)d)>",
        datefmt="%Y-%m-%dT%H:%M:%S",
        level=log_level,
    )
    LOGGER = logging.getLogger("FCS")
    sys.stderr.write = LOGGER.critical
    matplotlib.set_loglevel(plt_log_level)


try:
    if not os.path.exists("./src/res/config.json"):
        raise FileNotFoundError("Config file not found!")
    import utils

    configure_logging(utils.config["log_level"])
    # utils.validate_setup()
except Exception as e:
    configure_logging("DEBUG", "DEBUG")
    log = logging.getLogger(__name__)
    log.critical(e, exc_info=True)
    sys.exit(1)

log = logging.getLogger(__name__)
log.debug(f"*** Flashcards {utils.config['version']} ***")

from main_window_gui import main_window_gui

mw = main_window_gui()
mw.launch_app()

log.debug("*** Application shutdown ***")
