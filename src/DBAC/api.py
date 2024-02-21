import pandas as pd
import os
from utils import fcc_queue, singleton, Config
from DBAC.db_queries import db_queries
from DBAC.db_efc import db_efc_queries
from DBAC.db_dataset_ops import db_dataset_ops, FileDescriptor

pd.options.mode.chained_assignment = None


@singleton
class DbOperator(db_queries, db_efc_queries, db_dataset_ops):
    def __init__(self):
        self.config = Config()
        self.__configure()
        self.__validate_env()
        db_dataset_ops.__init__(self)
        db_queries.__init__(self)
        self.refresh()
        self.get_files()

    def __configure(self):
        self.KINDS = type(
            "FileKindsEnum",
            (object,),
            {"mst": "M", "lng": "L", "rev": "R", "eph": "E", "unk": "U"},
        )()
        self.KFN = {
            "M": "Mistakes", "L": "Language", "R": "Revision", "E": "Ephemeral", "U": "Unknown"
        }
        self.GRADED = {self.KINDS.rev, self.KINDS.mst, self.KINDS.eph}
        self.RES_PATH = "./src/res/"
        self.DB_PATH = "./src/res/db.csv"
        self.DATA_PATH = "./data/"
        self.REV_DIR = "rev"
        self.LNG_DIR = "lng"
        self.MST_DIR = "mst"
        self.TSFORMAT = r"%Y-%m-%dT%H:%M:%S"
        self.DB_COLS = (
            "TIMESTAMP",
            "SIGNATURE",
            "LNG",
            "TOTAL",
            "POSITIVES",
            "SEC_SPENT",
            "KIND",
        )

    def __validate_env(self):
        if not os.path.exists(self.DB_PATH):
            pd.DataFrame(columns=self.DB_COLS).to_csv(
                self.DB_PATH, sep=";", encoding="utf-8", index=False
            )
            fcc_queue.put(f"Initialized a new Database: {self.DB_PATH}")

        if not os.path.exists(self.DATA_PATH):
            os.makedirs(self.DATA_PATH)
            fcc_queue.put(f"Created a new Data path: {self.DATA_PATH}")
