import PyQt5.QtWidgets as widget
from PyQt5 import QtGui
from utils import load_config



class Mistakes(widget.QWidget):

    def __init__(self, mistakes_list, main_window):
        self.config = load_config()
        self.default_side = self.config['card_default_side']
        self.mistakes_list = mistakes_list
        self.main_window = main_window
        super(Mistakes, self).__init__(None)

        # Window Parameters
        self.left = 10
        self.top = 10
        self.width = 400
        self.height = 44 * len(self.mistakes_list)
        self.buttons_height = 45

        self.arrange_window()
    

    def arrange_window(self):
        self.setWindowTitle('Mistakes')
        self.setWindowIcon(QtGui.QIcon(self.config['resources_path'] + '\\icon.png'))
        self.setGeometry(self.left, self.top, self.width, self.height)
        self.center()

        # Style
        self.setStyleSheet(self.config['main_style_sheet'])
        self.textbox_stylesheet = (self.config['textbox_style_sheet'])
        self.button_style_sheet = self.config['button_style_sheet']
        self.font = self.config['font']
        self.font_button_size = self.config['efc_button_font_size']
        self.button_font = QtGui.QFont(self.font, self.font_button_size)

        # Elements
        self.layout = widget.QGridLayout()
        self.setLayout(self.layout)
        self.layout.addWidget(self.create_mistakes_list_default_side(), 0, 0)
        self.layout.addWidget(self.create_mistakes_list_alternate_side(), 0, 1)
        

    def create_mistakes_list_default_side(self):
        self.mistakes_list_default_side = widget.QListWidget(self)
        self.mistakes_list_default_side.setFont(self.button_font)
        self.mistakes_list_default_side.setStyleSheet(self.textbox_stylesheet)
        [self.mistakes_list_default_side.addItem(m[self.default_side]) for m in self.mistakes_list]
        return self.mistakes_list_default_side
    

    def create_mistakes_list_alternate_side(self):
        self.mistakes_list_alternate_side = widget.QListWidget(self)
        self.mistakes_list_alternate_side.setFont(self.button_font)
        self.mistakes_list_alternate_side.setStyleSheet(self.textbox_stylesheet)
        [self.mistakes_list_alternate_side.addItem(m[1-self.default_side]) for m in self.mistakes_list]
        return self.mistakes_list_alternate_side


    def center(self):
        frame_geo = self.frameGeometry()
        target_pos = widget.QDesktopWidget().availableGeometry().center()
        frame_geo.moveCenter(target_pos)
        self.move(frame_geo.topLeft())


    # def closeEvent(self, a0: QtGui.QCloseEvent) -> None:
    #     self.main_window.load_button_click()