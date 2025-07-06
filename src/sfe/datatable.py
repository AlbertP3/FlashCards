from PyQt5.QtCore import Qt, QAbstractTableModel, QVariant, QModelIndex, QEvent
from PyQt5.QtWidgets import QStyledItemDelegate, QLineEdit
from PyQt5.QtGui import QCursor
import logging
from sfe.fh import get_filehandler

log = logging.getLogger("SFE")


class DelegatedLineEdit(QLineEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.installEventFilter(self)

    def focusInEvent(self, event):
        QLineEdit.focusInEvent(self, event)
        self.deselect()

    def eventFilter(self, obj, event):
        if event.type() == QEvent.Show:
            global_pos = QCursor.pos()
            local_pos = self.mapFromGlobal(global_pos)
            index = self.cursorPositionAt(local_pos)
            self.setCursorPosition(index)
        return super().eventFilter(obj, event)


class QTableItemDelegate(QStyledItemDelegate):
    def createEditor(self, parent, option, index):
        return DelegatedLineEdit(parent)


class DataTableModel(QAbstractTableModel):
    def __init__(self, filepath: str):
        super().__init__()
        self.load(filepath)

    def with_reset_model(fn):
        def func(self, *args, **kwargs):
            self.beginResetModel()
            res = fn(self, *args, **kwargs)
            self.endResetModel()
            return res

        return func

    def rowCount(self, parent=None):
        return self.fh.total_visible_rows

    def columnCount(self, parent=None):
        return self.fh.total_columns

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if role == Qt.CheckStateRole:
            return None
        try:
            return str(self.fh.data_view.iat[index.row(), index.column()])
        except IndexError:
            return None

    def headerData(self, col: int, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return self.fh.headers[col]
        return QVariant()

    def flags(self, index):
        return (
            Qt.ItemIsSelectable
            | Qt.ItemIsEnabled
            | Qt.ItemIsEditable & ~Qt.ItemIsUserCheckable
        )

    def setData(self, index, value: str, role=Qt.EditRole):
        if role == Qt.EditRole:
            col = index.column()
            row = index.row()
            idx = self.fh.data_view.index[row]
            if value != self.fh.src_data.iat[idx, col]:
                self.fh.update_cell(idx, col, value)
                self.fh.data_view.iat[row, col] = value
                self.dataChanged.emit(index, index)
                return True
        return False

    @with_reset_model
    def add_row(self, data: list[str]):
        self.fh.create_row(data)
        if self.fh.query:
            self.fh.filter(self.fh.query)

    @with_reset_model
    def del_rows(self, rows: list[int]):
        self.fh.delete_rows(rows)
        if self.fh.query:
            self.fh.filter(self.fh.query)

    @with_reset_model
    def filter(self, query: str):
        self.fh.filter(query)

    @with_reset_model
    def remove_filter(self):
        self.fh.remove_filter()    

    @with_reset_model
    def load(self, filepath: str):
        self.fh = get_filehandler(filepath)
        self.fh.load_data()

    @with_reset_model
    def reload(self):
        self.fh.load_data()
        if self.fh.query:
            self.fh.filter(self.fh.query)
