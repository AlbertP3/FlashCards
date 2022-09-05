import os
from utils import register_log

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
    register_log(CONFIG_NOT_FOUND_TEXT)

