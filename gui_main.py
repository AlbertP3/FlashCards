import sys

from PyQt5 import QtCore
from utils import *
import logic
import PyQt5.QtWidgets as widget
from PyQt5.QtCore import pyqtSlot
from PyQt5 import QtGui
import pandas as pd
from random import randint


def __launch_main_window():
    # keep a reference to the opened window, 
    # otherwise it goes out of scope and is garbage collected
    mw = main_window()
    mw.show()
    return mw


class main_window(widget.QWidget):
    # Everything user sees is a widget
    # self.load_button.clicked.connect(self.dummy_insert) <- func w/o args

    def __init__(self):
        super().__init__()

        # Flashcards parameters
        self.revmode = 'OFF'
        self.total_words = 0
        self.current_index = 0
        self.dataset = None
        self.side = 0

        # Window Parameters
        self.left = 10
        self.top = 10
        self.width = 475
        self.height = 450
        self.textbox_height = 280
        self.buttons_height = 45

        # Set Parameters
        self.setWindowTitle('LlamaLearning')
        self.setGeometry(self.left, self.top, self.width, self.height)

        # Layout & Style
        self.layout = widget.QGridLayout()
        self.setLayout(self.layout)
        self.font = 'Poppins'
        self.font_button_size = 12
        self.font_textbox_size = 32
        self.textbox_font = QtGui.QFont(self.font, self.font_textbox_size)
        self.button_font = QtGui.QFont(self.font, self.font_button_size)
        
        # see available styles
        # print(PyQt5.QtWidgets.QStyleFactory.keys())
        # self.setStyle(widget.QStyleFactory.create('WindowsXP'))

        self.setStyleSheet("""
        background-color: rgb(31,31,31); 
        color: rgb(211,211,211);
        margin:0px; 
        border:1px solid rgb(211, 211, 211);
        padding:0px;
        """)
        
        self.layout_first_row = widget.QGridLayout()
        self.layout_second_row = widget.QGridLayout()
        self.layout_third_row = widget.QGridLayout()
        self.layout_fourth_row = widget.QGridLayout()

        self.layout.addLayout(self.layout_first_row, 0, 0)
        self.layout.addLayout(self.layout_second_row, 1, 0)
        self.layout.addLayout(self.layout_third_row, 2, 0)
        self.layout.addLayout(self.layout_fourth_row, 3, 0)

        # Widgets
        self.layout_first_row.addWidget(self.textbox(), 0, 0)

        self.layout_second_row.addWidget(self.prev_button(), 0, 0)
        self.layout_second_row.addWidget(self.reverse_button(), 0, 1)
        self.layout_second_row.addWidget(self.next_button(), 0, 2)

        self.layout_third_row.addWidget(self.load_button(), 2, 0)
        self.layout_third_row.addWidget(self.del_button(), 2, 1)
        self.layout_third_row.addWidget(self.efc_button(), 2, 2)
        self.layout_third_row.addWidget(self.save_button(), 2, 3)

        self.layout_fourth_row.addWidget(self.score_button(), 3, 0)
        self.layout_fourth_row.addWidget(self.settings_button(), 3, 1)
        self.layout_fourth_row.addWidget(self.load_again_button(), 3, 2)
        self.layout_fourth_row.addWidget(self.words_button(), 3, 3)
        self.layout_fourth_row.addWidget(self.revmode_button(), 3, 4)
        

        # Execute
        self.center()
        self.show()
    

    def textbox(self):
        self.textbox = widget.QTextEdit(self)
        self.textbox.setFixedHeight(self.textbox_height)
        self.textbox.setFont(self.textbox_font)
        self.textbox.setStyleSheet('''
            color: rgb(11,11,11); 
            background-color: rgb(155,255,160); 
            ''')
        self.textbox.setAlignment(QtCore.Qt.AlignCenter)
        return self.textbox


    def load_button(self):
        self.load_button = widget.QPushButton('Load', self)
        self.load_button.setFixedHeight(self.buttons_height)
        self.load_button.setFont(self.button_font)
        self.load_button.setText('Load')
        self.load_button.clicked.connect(self.load_button_click)
        return self.load_button

    def prev_button(self):
        self.prev_button = widget.QPushButton(self)
        self.prev_button.setFixedHeight(self.buttons_height)
        self.prev_button.setFont(self.button_font)
        self.prev_button.setText('Prev')
        self.prev_button.clicked.connect(self.click_prev)
        return self.prev_button

    def next_button(self):
        self.next_button = widget.QPushButton(self)
        self.next_button.setFixedHeight(self.buttons_height)
        self.next_button.setFont(self.button_font)
        self.next_button.setText('Next')
        self.next_button.clicked.connect(self.click_next)
        return self.next_button

    def reverse_button(self):
        self.reverse_button = widget.QPushButton(self)
        self.reverse_button.setFixedHeight(self.buttons_height)
        self.reverse_button.setFont(self.button_font)
        self.reverse_button.setText('Reverse')
        self.reverse_button.clicked.connect(self.reverse_side)
        return self.reverse_button

    def score_button(self):
        self.score_button = widget.QPushButton(self)
        self.score_button.setFixedHeight(self.buttons_height)
        self.score_button.setText('<>')
        return self.score_button

    def settings_button(self):
        settings_button = widget.QPushButton(self)
        settings_button.setFixedHeight(self.buttons_height)
        settings_button.setText('⚙')
        # settings_button.clicked.connect()
        return settings_button

    def save_button(self):
        save_button = widget.QPushButton(self)
        save_button.setFixedHeight(self.buttons_height)
        save_button.setText('Save')
        # save_button.clicked.connect()
        return save_button

    def del_button(self):
        del_button = widget.QPushButton(self)
        del_button.setFixedHeight(self.buttons_height)
        del_button.setText('🗑')
        # del_button.clicked.connect()
        return del_button

    def load_again_button(self):
        load_again_button = widget.QPushButton(self)
        load_again_button.setFixedHeight(self.buttons_height)
        load_again_button.setText('⟳')
        # load_again_button.clicked.connect()
        return load_again_button

    def revmode_button(self):
        self.revmode_button = widget.QPushButton(self)
        self.revmode_button.setFixedHeight(self.buttons_height)
        self.revmode_button.setText('RM:{}'.format(self.revmode))
        self.revmode_button.clicked.connect(self.change_revmode)
        return self.revmode_button

    def efc_button(self):
        efc_button = widget.QPushButton(self)
        efc_button.setFixedHeight(self.buttons_height)
        efc_button.setText('📜')
        return efc_button

    def words_button(self):
        self.words_button = widget.QPushButton(self)
        self.words_button.setFixedHeight(self.buttons_height)
        self.set_words_button_text()
        return self.words_button


    def reverse_side(self):
        self.side = 1 - self.side
        self.insert_text(self.get_current_card())
        

    def append_current_index(self):
        if self.current_index < self.total_words - 1:
            self.current_index += 1
            self.set_words_button_text()


    def decrease_current_index(self):
        if self.current_index >= 1:
            self.current_index -= 1
            self.set_words_button_text()


    def set_words_button_text(self):
        self.words_button.setText('{}/{}'.format(self.current_index+1, self.total_words))


    def click_next(self):
        self.append_current_index()
        self.insert_text(self.get_current_card())


    def click_prev(self):
        self.decrease_current_index()
        self.insert_text(self.get_current_card())


    def center(self):
        frame_geo = self.frameGeometry()
        target_pos = widget.QDesktopWidget().availableGeometry().center()
        frame_geo.moveCenter(target_pos)
        self.move(frame_geo.topLeft())


    def insert_text(self, text, default_font=14):
        dynamic_font_size = 32 - int(len(text)/4)
        self.font_textbox_size = dynamic_font_size if dynamic_font_size > 0 else default_font
        self.textbox_font = QtGui.QFont(self.font, self.font_textbox_size)
        self.textbox.setFont(self.textbox_font)
        self.textbox.setText(text)
        self.textbox.setAlignment(QtCore.Qt.AlignCenter)


    def set_score(self, pos, total):
        score = pos/total if total != 0 else '<>'
        self.score_button.setText('{}'.format(score))


    def change_revmode(self):
        self.revmode = 'ON' if self.revmode == 'OFF' else 'OFF'
        self.revmode_button.setText('RM:{}'.format(self.revmode))


    def load_button_click(self):
        self.dataset = logic.load_dataset()
        self.total_words = self.dataset.shape[0]
        self.set_words_button_text()
        self.insert_text(self.get_current_card())


    def get_current_card(self):
        return self.dataset.iloc[self.current_index, self.side]
                


def launch():
    # [] or sys.argv represent cmd lines passed to the application
    app = widget.QApplication([])
    window = __launch_main_window()
    app.exec()
    return window


if __name__ == '__main__':
    window = launch()
    window.insert_text('Hello World')