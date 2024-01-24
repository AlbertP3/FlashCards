import pandas as pd
from utils import *
from DBAC.db_queries import db_queries
from DBAC.db_efc import db_efc_queries
from DBAC.db_dataset_ops import db_dataset_ops, FileDescriptor

pd.options.mode.chained_assignment = None


@singleton
class DbOperator(db_queries, db_efc_queries, db_dataset_ops):
    def __init__(self):
        self.__configure()
        self.config = Config()
        db_dataset_ops.__init__(self)
        db_queries.__init__(self)
        self.refresh()
        self.get_files()

    def __configure(self):
        self.KINDS = type(
            "FileKindsEnum",
            (object,),
            {"mst": "mistakes", "lng": "language", "rev": "revision"},
        )()
        self.GRADED = {self.KINDS.rev, self.KINDS.mst}
        self.RES_PATH = "./src/res/"
        self.DB_PATH = "./src/res/db.csv"
        self.DATA_PATH = "./data/"
        self.REV_DIR = "rev"
        self.LNG_DIR = "lng"
        self.MST_DIR = "mst"
        self.TSFORMAT = r"%Y-%m-%dT%H:%M:%S"
