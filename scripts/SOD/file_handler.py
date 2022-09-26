import pandas as pd
import openpyxl

class file_handler:

    def __init__(self, path, ws):
        self.path = path
        self.wb = openpyxl.load_workbook(self.path)
        self.ws = self.wb[ws]
        self.data = {self.ws.cell(r, 1).value for r in range(1, self.ws.max_row+1)}
    

    def append_content(self, foreign_word, domestic_word) -> tuple[bool, str]:    
        target_row = self.ws.max_row + 1
        if self.ws.cell(row=target_row, column=1).value is None:
            self.ws.cell(row=target_row, column=1, value=foreign_word)
            self.ws.cell(row=target_row, column=2, value=domestic_word)
            self.data.add(foreign_word)
            self.wb.save(self.path)
            return True, ''
        else:
            return False, '[WARNING] Target Cell is not empty!'


    def is_duplicate(self, word) -> bool:
        return word in self.data
        

    def close(self):
        self.wb.close()
