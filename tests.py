import unittest
import gui_main as gui_main
import logic
import db_api
import pandas as pd
from utils import *
import tkinter as tk
import PyQt5.QtWidgets
import mistakes_dialog


class functional_tests(unittest.TestCase):
    
    def test_available_styles(self):
        print(PyQt5.QtWidgets.QStyleFactory.keys())
        

class unit_tests(unittest.TestCase):
    pass


if __name__ == '__main__':
    # unittest.main()
    # logic.update_config('onload_file_path', './revisions/REV_RU11172021073015.csv')
    db_query = db_api.db_interface()
    # print(db_query.get_first_date('REV_RU11172021073015').__class__)
    print((make_todayte() - make_date('11/07/2021, 08:48:04')).days)