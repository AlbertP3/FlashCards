import unittest
import gui_main as gui_main
import logic
import db_api
import pandas as pd
from utils import *
import tkinter as tk
import PyQt5.QtWidgets
import efc
import mistakes_dialog


class functional_tests(unittest.TestCase):
    
    def test_available_styles(self):
        print(PyQt5.QtWidgets.QStyleFactory.keys())
        

class unit_tests(unittest.TestCase):
    pass


if __name__ == '__main__':
    # unittest.main()
    # logic.update_config('onload_file_path', './revisions/REV_RU11172021073015.csv')
    print(get_relative_path_from_abs_path('C:/Users/blueg/Documents/workspace_it/Flashcards/languages/ru.csv'))
