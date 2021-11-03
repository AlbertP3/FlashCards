import unittest
import gui_main as gui_main
from utils import *
import tkinter as tk
import PyQt5.QtWidgets
import threading

class functional_tests(unittest.TestCase):
    
    def test_available_styles(self):
        print(PyQt5.QtWidgets.QStyleFactory.keys())
        

class unit_tests(unittest.TestCase):
    pass


if __name__ == '__main__':
    unittest.main()