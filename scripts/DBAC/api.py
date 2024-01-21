import pandas as pd
from utils import *
from DBAC.db_queries import db_queries
from DBAC.db_efc import db_efc_queries
from DBAC.db_dataset_ops import db_dataset_ops, FileDescriptor

pd.options.mode.chained_assignment = None



@singleton
class db_interface(
    db_queries, 
    db_efc_queries, 
    db_dataset_ops
    ):
    def __init__(self):
        self.config = Config()
        db_dataset_ops.__init__(self)
        db_queries.__init__(self)
        self.refresh()
        self.get_files()        
