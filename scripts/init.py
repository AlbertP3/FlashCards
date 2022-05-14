import os
from datetime import datetime
from utils import register_log

setup_success = True
try:
    if 'config.ini' not in os.listdir('./scripts/resources/'):
        setup_status = "Config file was not found. Pleace follow the setup instructions: place the Launcher in the directory with scripts folder."
        setup_success = False
except FileNotFoundError as e:
        setup_status = e
        setup_success = False
    
if setup_success:
    from main_window_gui import main_window_gui
    from utils import validate_setup
    validate_setup()
    mw = main_window_gui()
    mw.launch_app()
else:
    register_log(setup_status)

