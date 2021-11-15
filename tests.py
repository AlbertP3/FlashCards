import unittest
import gui_main as gui_main
import logic
from utils import *
import tkinter as tk
import PyQt5.QtWidgets


class functional_tests(unittest.TestCase):
    
    def test_available_styles(self):
        print(PyQt5.QtWidgets.QStyleFactory.keys())
        

class unit_tests(unittest.TestCase):
    pass


if __name__ == '__main__':
    # unittest.main()
    print(logic.load_config()['font_button_size'])