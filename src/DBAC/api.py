import pandas as pd
import os
import logging
from dataclasses import dataclass
from utils import singleton
from DBAC.db_queries import DBQueries
from DBAC.db_efc import DbEFCQueries
from DBAC.db_dataset_ops import DbDatasetOps

log = logging.getLogger("DBA")
pd.options.mode.chained_assignment = None


@dataclass
class FlashCardKinds:
    mst = "M"
    lng = "L"
    rev = "R"
    eph = "E"
    unk = "U"


@singleton
class DbOperator(DBQueries, DbEFCQueries, DbDatasetOps):
    def __init__(self):
        self.__configure()
        self.__validate_env()
        DbDatasetOps.__init__(self)
        DBQueries.__init__(self)
        self.load()
        self.update_fds()

    def __configure(self):
        self.KINDS = FlashCardKinds()
        self.KFN = {
            "M": "Mistakes",
            "L": "Language",
            "R": "Revision",
            "E": "Ephemeral",
            "U": "Unknown",
        }
        self.GRADED = {self.KINDS.rev, self.KINDS.mst, self.KINDS.eph}
        self.RES_PATH = "./src/res/"
        self.DB_PATH = "./src/res/db.csv"
        self.DATA_PATH = "./data/"
        self.TMP_BACKUP_PATH = "./src/res/tmpfcs.csv"
        self.REV_DIR = "rev"
        self.LNG_DIR = "lng"
        self.MST_DIR = "mst"
        self.TSFORMAT = r"%Y-%m-%dT%H:%M:%S"
        self.MST_BASENAME = "{lng}_mistakes_"
        self.DB_COLS = (
            "TIMESTAMP",
            "SIGNATURE",
            "LNG",
            "TOTAL",
            "POSITIVES",
            "SEC_SPENT",
            "KIND",
            "IS_FIRST",
        )

    def __validate_env(self):
        if not os.path.exists(self.DB_PATH):
            pd.DataFrame(columns=self.DB_COLS).to_csv(
                self.DB_PATH, sep=";", encoding="utf-8", index=False
            )
            log.info(f"Initialized a new Database: {self.DB_PATH}")

        if not os.path.exists(self.DATA_PATH):
            os.makedirs(self.DATA_PATH)
            log.info(f"Created a new Data path: {self.DATA_PATH}")


db = DbOperator()
