import os
import sys
import logging
import matplotlib

CWD = os.path.dirname(os.path.abspath(__file__))

# Configure logging
logging.basicConfig(
    filename=os.path.realpath(f'{CWD}/../fcs.log'),
    filemode='a',
    format='%(asctime)s.%(msecs)05d [%(name)s] %(levelname)s %(message)s <%(filename)s(%(lineno)d)>',
    datefmt="%Y-%m-%dT%H:%M:%S", 
    level='ERROR'
    )
LOGGER = logging.getLogger('FCS')
sys.stderr.write = LOGGER.critical
log = logging.getLogger(__name__)
matplotlib.set_loglevel('error')


# Continue setup
setup_success = True
CONFIG_NOT_FOUND_TEXT = "Config file was not found. Pleace follow the setup instructions: place the Launcher in the directory with scripts folder."

if 'config.ini' not in os.listdir('./scripts/resources/'):
    setup_success = False
    
if setup_success:
    from main_window_gui import main_window_gui
    from utils import validate_setup
    validate_setup()
    mw = main_window_gui()
    mw.launch_app()
else:
    log.error(CONFIG_NOT_FOUND_TEXT)
