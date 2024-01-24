from utils import *
import DBAC.api as api


class Timespent_BE:

    def __init__(self):
        self.config = Config()


    def get_timespent_printout(self, last_n, interval):
        data = self._get_data_for_timespent(last_n, interval)
        printout = self._format_timespent_data(data)
        return printout


    def _get_data_for_timespent(self, last_n, interval):
            db_interface = api.db_interface()
            db_interface.refresh()
            lngs = self.config['languages']
            db = db_interface.get_filtered_by_lng(lngs)

            date_format_dict = {
                'm': '%m/%Y',
                'd': '%d/%m/%Y',
                'y': '%Y',
            } 
            date_format = date_format_dict[interval]
            db['TIMESTAMP'] = pd.to_datetime(db['TIMESTAMP']).dt.strftime(date_format)

            # create column with time for each lng in config
            grand_total_time = list()
            for l in lngs:  
                db[l] = db.loc[db.iloc[:, 1].str.contains(l)]['SEC_SPENT']
                grand_total_time.append(db[l].sum())

            # group by selected interval - removes SIGNATURE
            db = db.groupby(db['TIMESTAMP'], as_index=False, sort=False).sum()
            
            # cut db
            db = db.iloc[-last_n:, :]
            try:
                db = db.loc[db.iloc[:, 4] != 0]
            except IndexError:
                self.post_fcc(f'DATE  {"  ".join(lngs)}{"  TOTAL" if len(lngs)>1 else ""}')
                return

            # format dates in time-containing columns
            visible_total_time = list()
            for l in lngs:
                visible_total_time.append(db[l].sum())
                db[l] = db[l].apply(lambda x: ' ' + format_seconds_to(x, 'hour', null_format='-', rem=2, sep=':'))
            db['SEC_SPENT'] = db['SEC_SPENT'].apply(lambda x: ' ' + format_seconds_to(x, 'hour', null_format='-', rem=2, sep=':'))

            self.visible_total_time = visible_total_time
            self.gt_times = grand_total_time
            return db
            

    def _format_timespent_data(self, db:pd.DataFrame) -> str:
            lngs = self.config['languages']
            col_space = len(str(sum(self.gt_times)//3600)) + 3
            if len(lngs) > 1:
                res = db.to_string(index=False, columns=['TIMESTAMP']+lngs+['SEC_SPENT'], header=['DATE']+lngs+['TOTAL'], col_space=col_space)
                self.visible_total_time.append(sum(self.visible_total_time))
                self.gt_times.append(sum(self.gt_times))
            else:
                res = db.to_string(index=False, columns=['TIMESTAMP']+lngs, header=['DATE']+['TOTAL'], col_space=col_space)

            # add row for Grand Total
            self.visible_total_time = [format_seconds_to(t, "hour", null_format="-", pref_len=col_space, sep=':', rem=2) for t in self.visible_total_time]
            self.gt_times = [format_seconds_to(t, "hour", null_format="-", pref_len=col_space, sep=':', rem=2) for t in self.gt_times]
            res += '\n' + '-'*len(res.split('\n')[1])
            res += '\n∑       ' + ' '.join(self.visible_total_time)
            res += '\nTOTAL   ' + ' '.join(self.gt_times)
            return res



