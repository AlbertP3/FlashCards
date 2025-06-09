from PyQt5.QtCore import Qt, QAbstractTableModel, QVariant, QModelIndex
from PyQt5.QtGui import QColor
import logging
from sfe.fh import get_filehandler
from cfg import config

log = logging.getLogger("SFE")


class DataTableModel(QAbstractTableModel):
    def __init__(self, filepath: str):
        super().__init__()
        self.highlighted_rows = set()
        self.load(filepath)

    def with_reset_model(fn):
        def func(self, *args, **kwargs):
            self.beginResetModel()
            res = fn(self, *args, **kwargs)
            self.endResetModel()
            return res

        return func

    def rowCount(self, parent=None):
        return self.fh.total_rows

    def columnCount(self, parent=None):
        return self.fh.total_columns

    def data(self, index: QModelIndex, role=Qt.DisplayRole):
        if role == Qt.CheckStateRole:
            return None
        elif role == Qt.BackgroundRole and index.row() in self.highlighted_rows:
            return QColor(config.table_view["new_row_color"])
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
            idx = self.fh.data_view.iat[index.row(), -1]
            col = index.column()
            if value != self.fh.src_data.iat[idx, col]:
                self.fh.update_cell(idx, col, value)
                self.fh.data_view.iat[index.row(), index.column()] = value
                self.dataChanged.emit(index, index)
                return True
        return False

    @with_reset_model
    def add_row(self, row: list[str]):
        self.fh.add_cell(row)
        if self.fh.query:
            self.fh.filter(self.fh.query)
        self.set_highlighted_rows()

    @with_reset_model
    def del_rows(self, rows: list[int]):
        self.fh.delete_rows(rows)
        if self.fh.query:
            self.fh.filter(self.fh.query)
        self.set_highlighted_rows()

    @with_reset_model
    def filter(self, query: str):
        self.fh.filter(query)

    @with_reset_model
    def load(self, filepath: str):
        self.fh = get_filehandler(filepath)
        self.fh.load_data()
        self.set_highlighted_rows()

    @with_reset_model
    def lookup(self, query: str, col: int) -> str:
        self.fh.remove_filter()
        self.fh.filter(query)
        return self.fh.lookup(col)

    @with_reset_model
    def reload(self):
        self.fh.load_data()
        self.set_highlighted_rows()

    def set_highlighted_rows(self):
        try:
            cached_rows = config["ILN"][self.fh.filepath]
            self.highlighted_rows = set(range(cached_rows, self.fh.total_rows))
        except KeyError:
            pass
