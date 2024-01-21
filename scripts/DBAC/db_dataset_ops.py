import re
from itertools import chain
import random
import logging
import pandas as pd
from functools import cache
from datetime import datetime
from dataclasses import dataclass
import os
import csv
from utils import fcc_queue, get_files_in_dir

log = logging.getLogger('DBAC')

@dataclass
class FileDescriptor:
    basename:   str           = None
    filepath:   str           = None
    lng:        str           = None
    kind:       str           = None    # [language, revision, mistakes]
    ext:        str           = None    # [.csv, .xlsx, ...]
    valid:      bool          = None
    data:       pd.DataFrame  = None
    signature:  str           = None
    tmp:        bool          = False
    mtime:      int           = None

    def __str__(self) -> str:
        return f"{self.filepath}"
    
    def __eq__(self, __value: object) -> bool:
        return self.filepath == __value.filepath



class db_dataset_ops():

    def __init__(self):
        self.empty_df = pd.DataFrame(data=[['-','-']])
        self.__AF = FileDescriptor(tmp=True, data=self.empty_df)
    
    @property
    def active_file(self):
        return self.__AF
    
    @active_file.setter
    def active_file(self, fd:FileDescriptor):
        self.validate_dataset(fd)
        if not fd.valid:
            fd.data = self.empty_df
            fd.tmp = True
        if self.__AF != fd:
            self.__AF.data = None
        self.__AF = fd
        log.debug(f"Set {'Valid' if self.__AF.valid else 'Invalid'} {'Temporary' if self.__AF.tmp else 'Regular'} Active File: {self.__AF}")
        if (fdwd:=sum(1 for f in self.files.values() if f.data is not None)) > 1:
            log.warning(f"There are {fdwd} FileDescriptors with data!")
    
    def reload_files_cache(self):
        self.get_files.cache_clear();            self.get_files()
        self.get_sorted_revisions.cache_clear(); self.get_sorted_revisions()
        self.get_sorted_languages.cache_clear(); self.get_sorted_languages()
        self.get_sorted_mistakes.cache_clear(); self.get_sorted_mistakes()
        self.match_from_all_languages.cache_clear()

    @staticmethod
    def gen_signature(language) -> str:
        saving_date = datetime.now().strftime('%m%d%Y%H%M%S')
        signature = f'REV_{language}{saving_date}'
        return signature

    def save_revision(self, dataset:pd.DataFrame) -> str:
        '''Creates a new file for the Revision. Returns a new filepath'''
        signature = self.gen_signature(self.active_file.lng)
        try:
            fp = os.path.join(
                self.config['revs_path'], 
                self.active_file.lng, 
                f"{signature}.csv")
            dataset.to_csv(fp, index=False)
            fcc_queue.put(f'{signature} saved successfully')
            log.debug(f"Created a new File: {fp}")
            self.reload_files_cache()
            return fp
        except Exception as e:
            fcc_queue.put(f'Exception while creating File: {e}')
            log.error(e, exc_info=True)

    def save_language(self, dataset:pd.DataFrame, fd:FileDescriptor) -> str:
        '''Dump dataset to the Language/Mistakes file. Returns operation status'''
        try:
            if fd.ext in ['.csv', '.txt']:
                dataset.to_csv(fd.filepath, index=False, mode='w', header=True, sep=';')
                opstatus = f"Saved content to {fd.filepath}"
            elif fd.ext in ['.xlsx', '.xlsm']:
                dataset.to_excel(fd.filepath, sheet_name=fd.lng, index=False)
                opstatus = f"Saved content to {fd.filepath}"
            else:
                opstatus = f'Unsupported Extension: {fd.ext}'
        except FileNotFoundError as e:
            opstatus = f'File {fd.filepath} Not Found'
        except Exception as e:
            opstatus = f'Exception while creating File: {e}'
            log.error(e, exc_info=True)
        return opstatus

    def save_mistakes(self, mistakes_list:list, cols:list, offset:int) -> pd.DataFrame:
        '''Dump dataset to the Mistakes file'''
        lim = self.config['mistakes_buffer']
        mistakes_list:pd.DataFrame = pd.DataFrame(data=mistakes_list, columns=cols)
        basename = f'{self.active_file.lng}_mistakes'
        mfd = FileDescriptor(
            basename=basename,
            filepath=os.path.join(self.config['mistakes_path'], self.active_file.lng, basename+'.csv'),
            lng=self.active_file.lng,
            kind='revision',
            ext='.csv'
        )
        if mfd.filepath in self.files.keys():
            buffer = self.load_dataset(mfd, do_shuffle=False)
            buffer = pd.concat([buffer, mistakes_list.iloc[offset:]], ignore_index=True)
            buffer.iloc[-lim:].to_csv(
            mfd.filepath, index=False, mode='w', header=True
            )
            log.debug(f"Updated existing Mistakes File: {mfd.filepath}")
        else:
            mistakes_list.iloc[:lim].to_csv(
                mfd.filepath, index=False, mode='w', header=True
            )
            log.debug(f"Created new Mistakes File: {mfd.filepath}")
            self.reload_files_cache()
        m_cnt = mistakes_list.shape[0] - offset
        msg = f'{m_cnt} card{"s" if m_cnt>1 else ""} saved to {mfd.filepath}'
        fcc_queue.put(msg)
        log.debug(msg)
        return mistakes_list

    def validate_dataset(self, fd:FileDescriptor) -> bool:
        if not isinstance(fd.data, pd.DataFrame):
            fd.valid = False
        else:
            if fd.data.shape[0] < 1:
                fd.valid = False
            elif fd.data.shape[1] >= 2:
                fd.valid = True
            else:
                fd.valid = False 
        return fd.valid
    
    def load_dataset(self, fd:FileDescriptor, do_shuffle=True, seed=None) -> pd.DataFrame:
        operation_status = ''
        try:
            if fd.ext in ['.csv', '.txt']:
                fd.data = self.read_csv(fd.filepath)
            elif fd.ext in ['.xlsx', '.xlsm']:  
                fd.data = self.read_excel(fd.filepath)
            elif fd.tmp:
                raise FileNotFoundError
            else:
                operation_status = f"Chosen extension is not (yet) supported: {fd.ext}"
        except FileNotFoundError as e:
            operation_status = f'File {fd.filepath} Not Found'
            log.debug(operation_status)
        except Exception as e:
            operation_status = f'Exception occurred: {e}'
            log.error(e, exc_info=True)

        self.active_file = fd
        if self.active_file.valid and do_shuffle:
            self.shuffle_dataset(seed)

        fcc_queue.put(operation_status)
        return fd.data
    
    def load_tempfile(self, data, kind, basename, lng, signature=None):
        fd = FileDescriptor(
            basename=basename,
            filepath=None,
            kind=kind,
            ext=None,
            lng=lng,
            data=data,
            valid=True,
            signature=signature or self.gen_signature(lng),  # TODO is it needed?
            tmp=True,
            mtime=99999999999
        )
        log.debug(f"Mocked a temporary file: {fd.basename}")
        self.active_file = fd

    def shuffle_dataset(self, seed=None):
        if not seed: pd_random_seed = random.randrange(10000)
        else: pd_random_seed = self.config['pd_random_seed']
        self.config.update({'pd_random_seed':pd_random_seed})
        self.__AF.data = self.__AF.data.sample(
            frac=1, random_state=pd_random_seed).reset_index(
                drop=True
        )

    def read_csv(self, file_path):
        dataset = pd.read_csv(
            file_path, 
            encoding = 'utf-8',
            sep = self.get_dialect(file_path) if self.config.translate('csv_sniffer') else ','
        )   
        return dataset

    def get_dialect(self, dataset_path, investigate_rows=10):
        data = list()
        with open(dataset_path, 'r', encoding='utf-8') as csvfile:
            csvreader = csv.reader(csvfile)
            for r in csvreader:
                data.append(r)
                if len(data)>=investigate_rows:
                    break
        return csv.Sniffer().sniff(str(data[1]) + '\n' + str(data[2]), delimiters=self.config.translate('csv_sniffer')).delimiter

    def read_excel(self, file_path):
        return pd.read_excel(file_path, sheet_name=0)

    @cache
    def get_files(self) -> dict[str, FileDescriptor]:
        '''Finds files from 'revs_path' matching active Languages'''
        self.files = dict()
        for lng in self.config['languages']:
            self.__update_files(self.config['revs_path'], lng, kind='revision')
            self.__update_files(self.config['lngs_path'], lng, kind='language')
            self.__update_files(self.config['mistakes_path'], lng, kind='mistakes')
        log.debug(f"Collected FileDescriptors for {len(self.files)} files")
        return self.files
    
    def __update_files(self, path, lng, kind):
        try:
            for f in get_files_in_dir(os.path.join(path, lng)):
                basename, ext = os.path.splitext(f)
                filepath = os.path.join(path, lng, f)
                self.files[filepath] = FileDescriptor(
                    basename = basename,
                    filepath = filepath,
                    lng = lng,
                    kind = kind,
                    ext = ext,
                    signature=basename,
                    mtime=os.stat(filepath).st_mtime
                )
        except FileNotFoundError:
            log.warning(f"Language '{lng}' is missing the corresponding directory")
    
    @cache
    def get_sorted_revisions(self) -> list[FileDescriptor]:
        return sorted(
            [v for _, v in self.get_files().items() if v.kind=='revision'],
            key=lambda fd: self.get_first_datetime(fd.signature),
            reverse=True
        )
    
    @cache
    def get_sorted_languages(self) -> list[FileDescriptor]:
        return sorted(
            [v for _, v in self.get_files().items() if v.kind=='language'],
            key=lambda fd: fd.basename,
            reverse=True
        )
    
    @cache
    def get_sorted_mistakes(self) -> list[FileDescriptor]:
        return sorted(
            [v for _, v in self.get_files().items() if v.kind=='mistakes'],
            key=lambda fd: fd.basename,
            reverse=True
        )

    def delete_card(self, i):
        self.active_file.data.drop([i], inplace=True, axis=0)
        self.active_file.data.reset_index(inplace=True, drop=True)

    @cache
    def match_from_all_languages(self, repat:re.Pattern, exclude_dirs:re.Pattern=re.compile(r'.^')) -> list:
        return list(chain(
            *[
                [
                os.path.join(self.config['lngs_path'], d, f) 
                for f in os.listdir(os.path.join(self.config['lngs_path'], d)) 
                if repat.search(f)
                ]
            for d in os.listdir(self.config['lngs_path']) 
            if os.path.isdir(os.path.join(self.config['lngs_path'])) 
            and not exclude_dirs.search(os.path.basename(d))
            ]
        ))
