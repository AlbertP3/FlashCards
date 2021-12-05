import PyQt5.QtWidgets as widget
from PyQt5 import QtGui
from PyQt5.QtCore import Qt
from utils import *



class Close_dialog(widget.QWidget):

    def __init__(self, main_window):

        # Configuration
        self.config = load_config()
        super(Close_dialog, self).__init__(None)
        self.main_window = main_window

        # Window Parameters
        self.left = 10
        self.top = 10
        self.width = 220
        self.height = 120
        self.buttons_height = 45

        self.arrange_window()


    def arrange_window(self):

        self.setWindowTitle('Confirmation')
        self.setWindowIcon(QtGui.QIcon(self.config['resources_path'] + '\\icon.png'))
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.center()

        # Style
        self.setStyleSheet(self.config['main_style_sheet'])
        self.button_style_sheet = self.config['button_style_sheet']
        self.font = self.config['font']
        self.font_button_size = self.config['efc_button_font_size']
        self.button_font = QtGui.QFont(self.font, self.font_button_size)

        # Elements
        self.layout = widget.QGridLayout()
        self.setLayout(self.layout)
        self.layout.addWidget(self.create_prompt_text(), 0, 0, 1, 2)
        self.layout.addWidget(self.create_yes_button(), 1, 0)
        self.layout.addWidget(self.create_no_button(), 1, 1)
    

    def create_yes_button(self):
        self.yes_button = widget.QPushButton(self)
        self.yes_button.setFixedHeight(self.buttons_height)
        self.yes_button.setFont(self.button_font)
        self.yes_button.setText('Yes')
        self.yes_button.setStyleSheet(self.button_style_sheet)
        self.yes_button.clicked.connect(self.yes_button_click)
        return self.yes_button


    def create_no_button(self):
        self.no_button = widget.QPushButton(self)
        self.no_button.setFixedHeight(self.buttons_height)
        self.no_button.setFont(self.button_font)
        self.no_button.setText('No')
        self.no_button.setStyleSheet(self.button_style_sheet)
        self.no_button.clicked.connect(self.no_button_click)
        return self.no_button


    def create_prompt_text(self):
        self.prompt_text = widget.QLabel(self)
        self.prompt_text.setFixedHeight(self.buttons_height)
        self.prompt_text.setFont(self.button_font)
        self.prompt_text.setStyleSheet(self.button_style_sheet)
        self.prompt_text.setAlignment(Qt.AlignCenter)
        self.prompt_text.setText('Exit?')
        return self.prompt_text


    def yes_button_click(self):
        self.close()
        self.main_window.close()


    def no_button_click(self):
        self.close()


    def keyPressEvent(self, event):
        if event.key() == Qt.Key_Escape:
            # self.close()
            self.yes_button_click()
    

    def center(self):
        frame_geo = self.frameGeometry()
        target_pos = widget.QDesktopWidget().availableGeometry().center()
        frame_geo.moveCenter(target_pos)
        self.move(frame_geo.topLeft())