import unittest
import gui_main as gui_main
import logic
import db_api
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
    mst = mistakes_dialog.Mistakes()
    efc.launch_window()
