from abc import ABC
import pandas as pd



class db_efc_queries(ABC):

    def filter_for_efc_model(self):
        # Remove mistakes, obsolete lngs and revs with POSITIVES=0
        mistakes = {fd.signature for fd in self.files.values() if fd.kind == self.KINDS.mst}
        self.db = self.db[self.db['LNG'].isin(self.config['languages'])]
        self.db = self.db[~self.db['SIGNATURE'].isin(mistakes)]
        self.db = self.db.loc[self.db['POSITIVES'] != 0]
        self.filters['EFC_MODEL'] = True

    def add_efc_metrics(self, fill_timespent=False):
        # expands db with efc metrics and returns a dict consisting of per signature data
        self.db['TIMESTAMP'] = pd.to_datetime(self.db['TIMESTAMP'], format="%m/%d/%Y, %H:%M:%S")

        sig = {k:list() for k in self.db['SIGNATURE'].unique()}
        initial_reps = self.config['init_revs_cnt']
        if fill_timespent: avg_wpsec = self.db['TOTAL'].sum() / self.db.loc[self.db['SEC_SPENT'] > 0]['SEC_SPENT'].sum()
        else: avg_wpsec = 0
        rows_to_del = list()
        self.db['PREV_WPM'] = float(0)
        self.db['TIMEDELTA_SINCE_CREATION'] = 0
        self.db['TIMEDELTA_LAST_REV'] = 0
        self.db['CUM_CNT_REVS'] = 0
        self.db['PREV_SCORE'] = 0
        self.db['SCORE'] = 0

        for i, r in self.db.iterrows():
            s = r['SIGNATURE']
            # Tackle missing sec_spent
            if int(r['SEC_SPENT']) == 0: 
                if fill_timespent:
                    self.db.loc[i, 'SEC_SPENT'] = int(int(r['TOTAL'] / avg_wpsec))
                    r['SEC_SPENT'] = int(int(r['TOTAL'] / avg_wpsec))
                else:
                    rows_to_del.append(i)
                    continue
            # Skip initial repetitions
            sig[s].append((r['TIMESTAMP'], r['TOTAL'], r['POSITIVES'], r['SEC_SPENT']))
            if len(sig[s]) <= initial_reps:
                rows_to_del.append(i)
                continue
            # '-2' denotes previous revision
            self.db.loc[i, 'PREV_WPM'] = 60*sig[s][-2][1]/sig[s][-2][3]
            self.db.loc[i, 'CUM_CNT_REVS'] = len(sig[s])
            self.db.loc[i, 'TIMEDELTA_LAST_REV'] = int((sig[s][-1][0] - sig[s][-2][0]).total_seconds()/3600)
            self.db.loc[i, 'TIMEDELTA_SINCE_CREATION'] = int((sig[s][-1][0] - sig[s][0][0]).total_seconds()/3600)
            self.db.loc[i, 'PREV_SCORE'] = int(100*(sig[s][-2][2] / sig[s][-2][1]))
            self.db.loc[i, 'SCORE'] = int(100*sig[s][-1][2] / sig[s][-1][1])

        self.db = self.db.drop(index=rows_to_del, axis=0)
        self.filters['EFC_MODEL'] = True

    def remove_cols_for_efc_model(self):
        cols_to_remove = {'POSITIVES','TIMESTAMP','SIGNATURE','SEC_SPENT'}
        self.db = self.db.drop(cols_to_remove, axis=1)
        self.db = self.db.apply(pd.to_numeric, errors = 'coerce')
        self.filters['EFC_MODEL'] = True

    def gather_efc_record_data(self) -> dict:
        # Create a dictionary, mapping signatures to tuples of all matching revs
        self.db['TIMESTAMP'] = pd.to_datetime(self.db['TIMESTAMP'], format="%m/%d/%Y, %H:%M:%S")
        sig = {k:list() for k in self.db['SIGNATURE'].unique()}
        for i, r in self.db.iterrows():
            s = r['SIGNATURE']
            sig[s].append((r['TIMESTAMP'], r['TOTAL'], r['POSITIVES'], r['SEC_SPENT']))
        return sig
