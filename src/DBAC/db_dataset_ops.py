import re
import random
import logging
import pandas as pd
from functools import cache
from datetime import datetime
from dataclasses import dataclass
import os
import csv
from utils import fcc_queue

log = logging.getLogger("DBAC")


@dataclass
class FileDescriptor:
    basename: str = None
    filepath: str = None
    lng: str = None
    kind: str = None
    ext: str = None  # [.csv, .xlsx, ...]
    valid: bool = None
    data: pd.DataFrame = None
    signature: str = None
    tmp: bool = False
    mtime: int = None

    def __str__(self) -> str:
        return f"{self.filepath}"

    def __eq__(self, __value: object) -> bool:
        return self.filepath == __value.filepath


class db_dataset_ops:
    def __init__(self):
        self.empty_df = pd.DataFrame(data=[["-", "-"]])
        self.__AF = FileDescriptor(tmp=True, data=self.empty_df)

    @property
    def active_file(self):
        return self.__AF

    @active_file.setter
    def active_file(self, fd: FileDescriptor):
        self.validate_dataset(fd)
        if not fd.valid:
            fd.data = self.empty_df
            fd.tmp = True
        if self.__AF != fd:
            self.__AF.data = None
        self.__AF = fd
        log.debug(
            f"Set {'Valid' if self.__AF.valid else 'Invalid'} {'Temporary' if self.__AF.tmp else 'Regular'} Active File: {self.__AF}"
        )
        if (fdwd := sum(1 for f in self.files.values() if f.data is not None)) > 1:
            log.warning(f"There are {fdwd} FileDescriptors with data!")

    def make_filepath(self, lng: str, subdir: str, filename: str = "") -> os.PathLike:
        """Template for creating Paths"""
        return os.path.join(self.DATA_PATH, lng, subdir, filename)

    def reload_files_cache(self):
        self.get_files.cache_clear()
        self.get_files()
        self.get_sorted_revisions.cache_clear()
        self.get_sorted_revisions()
        self.get_sorted_languages.cache_clear()
        self.get_sorted_languages()
        self.get_sorted_mistakes.cache_clear()
        self.get_sorted_mistakes()
        self.match_from_all_languages.cache_clear()

    @staticmethod
    def gen_signature(language) -> str:
        saving_date = datetime.now().strftime("%d%m%Y%H%M%S")
        signature = f"REV_{language}{saving_date}"
        return signature

    def save_revision(self, dataset: pd.DataFrame) -> str:
        """Creates a new file for the Revision. Returns a new filepath"""
        try:
            fp = self.make_filepath(
                self.active_file.lng, self.REV_DIR, f"{self.active_file.signature}.csv"
            )
            dataset.to_csv(fp, index=False, encoding="utf-8")
            fcc_queue.put(f"Created {self.active_file.signature}")
            log.debug(f"Created a new File: {fp}")
            self.reload_files_cache()
            return fp
        except Exception as e:
            fcc_queue.put(f"Exception while creating File: {e}")
            log.error(e, exc_info=True)

    def save_language(self, dataset: pd.DataFrame, fd: FileDescriptor) -> str:
        """Dump dataset to the Language/Mistakes file. Returns operation status"""
        try:
            if fd.ext in [".csv", ".txt"]:
                dataset.to_csv(fd.filepath, index=False, mode="w", header=True, sep=";")
                opstatus = f"Saved content to {fd.filepath}"
            elif fd.ext in [".xlsx", ".xlsm"]:
                dataset.to_excel(fd.filepath, sheet_name=fd.lng, index=False)
                opstatus = f"Saved content to {fd.filepath}"
            else:
                opstatus = f"Unsupported Extension: {fd.ext}"
        except FileNotFoundError as e:
            opstatus = f"File {fd.filepath} Not Found"
        except Exception as e:
            opstatus = f"Exception while creating File: {e}"
            log.error(e, exc_info=True)
        return opstatus

    def save_mistakes(
        self, mistakes_list: list, cols: list, offset: int
    ) -> pd.DataFrame:
        """Dump dataset to the Mistakes file"""
        mistakes_list: pd.DataFrame = pd.DataFrame(data=mistakes_list, columns=cols)
        basename = f"{self.active_file.lng}_mistakes"
        mfd = FileDescriptor(
            basename=basename,
            filepath=self.make_filepath(
                self.active_file.lng, self.MST_DIR, basename + ".csv"
            ),
            lng=self.active_file.lng,
            kind=self.KINDS.mst,
            ext=".csv",
        )
        if mfd.filepath in self.files.keys():
            buffer = self.load_dataset(mfd, do_shuffle=False)
            buffer = pd.concat([buffer, mistakes_list.iloc[offset:]], ignore_index=True)
            buffer.iloc[-self.config["mistakes_buffer"] :].to_csv(
                mfd.filepath, index=False, mode="w", header=True
            )
            log.debug(f"Updated existing Mistakes File: {mfd.filepath}")
        else:
            mistakes_list.iloc[: self.config["mistakes_buffer"]].to_csv(
                mfd.filepath, index=False, mode="w", header=True
            )
            log.debug(f"Created new Mistakes File: {mfd.filepath}")
            self.reload_files_cache()
        m_cnt = mistakes_list.shape[0] - offset
        msg = f'{m_cnt} card{"s" if m_cnt>1 else ""} saved to {mfd.filepath}'
        fcc_queue.put(msg)
        log.debug(msg)
        return mistakes_list

    def validate_dataset(self, fd: FileDescriptor) -> bool:
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

    def load_dataset(
        self, fd: FileDescriptor, do_shuffle=True, seed=None
    ) -> pd.DataFrame:
        operation_status = ""
        try:
            if fd.ext in [".csv", ".txt"]:
                fd.data = self.read_csv(fd.filepath)
            elif fd.ext in [".xlsx", ".xlsm"]:
                fd.data = self.read_excel(fd.filepath)
            elif fd.tmp:
                raise FileNotFoundError
            else:
                operation_status = f"Chosen extension is not (yet) supported: {fd.ext}"
        except FileNotFoundError as e:
            operation_status = f"File {fd.filepath} Not Found"
            log.debug(operation_status)
        except Exception as e:
            operation_status = f"Exception occurred: {e}"
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
            signature=signature,
            tmp=True,
            mtime=99999999999,
        )
        log.debug(f"Mocked a temporary file: {fd.basename}")
        self.active_file = fd

    def shuffle_dataset(self, seed=None):
        if not seed:
            pd_random_seed = random.randrange(10000)
        else:
            pd_random_seed = self.config["pd_random_seed"]
        self.config.update({"pd_random_seed": pd_random_seed})
        self.__AF.data = self.__AF.data.sample(
            frac=1, random_state=pd_random_seed
        ).reset_index(drop=True)

    def read_csv(self, file_path):
        dataset = pd.read_csv(
            file_path,
            encoding="utf-8",
            sep=self.get_dialect(file_path)
            if self.config.translate("csv_sniffer")
            else ",",
        )
        return dataset

    def get_dialect(self, dataset_path, investigate_rows=10):
        data = list()
        with open(dataset_path, "r", encoding="utf-8") as csvfile:
            csvreader = csv.reader(csvfile)
            for r in csvreader:
                data.append(r)
                if len(data) >= investigate_rows:
                    break
        return (
            csv.Sniffer()
            .sniff(
                str(data[1]) + "\n" + str(data[2]),
                delimiters=self.config.translate("csv_sniffer"),
            )
            .delimiter
        )

    def read_excel(self, file_path):
        return pd.read_excel(file_path, sheet_name=0)

    @cache
    def get_files(self) -> dict[str, FileDescriptor]:
        """Finds files from 'revs_path' matching active Languages"""
        self.files = dict()
        for lng in self.config["languages"]:
            self.__update_files(lng, self.REV_DIR, kind=self.KINDS.rev)
            self.__update_files(lng, self.LNG_DIR, kind=self.KINDS.lng)
            self.__update_files(lng, self.MST_DIR, kind=self.KINDS.mst)
        log.debug(f"Collected FileDescriptors for {len(self.files)} files")
        return self.files

    def __update_files(self, lng, subdir, kind):
        try:
            for f in self.get_files_in_dir(self.make_filepath(lng, subdir)):
                basename, ext = os.path.splitext(os.path.basename(f))
                filepath = self.make_filepath(lng, subdir, f)
                self.files[filepath] = FileDescriptor(
                    basename=basename,
                    filepath=filepath,
                    lng=lng,
                    kind=kind,
                    ext=ext,
                    signature=basename,
                    mtime=os.stat(filepath).st_mtime,
                )
        except FileNotFoundError:
            log.warning(
                f"Language '{lng}' is missing the corresponding directory. Creating..."
            )
            self.create_language_dir_tree(lng)

    def create_language_dir_tree(self, lng: str):
        os.makedirs(self.make_filepath(lng, self.LNG_DIR))
        os.makedirs(self.make_filepath(lng, self.REV_DIR))
        os.makedirs(self.make_filepath(lng, self.MST_DIR))
        fcc_queue.put(f"Created directory tree for {lng}")

    @cache
    def get_sorted_revisions(self) -> list[FileDescriptor]:
        return sorted(
            [v for _, v in self.get_files().items() if v.kind == self.KINDS.rev],
            key=lambda fd: self.get_first_datetime(fd.signature),
            reverse=True,
        )

    @cache
    def get_sorted_languages(self) -> list[FileDescriptor]:
        return sorted(
            [v for _, v in self.get_files().items() if v.kind == self.KINDS.lng],
            key=lambda fd: fd.basename,
            reverse=True,
        )

    @cache
    def get_sorted_mistakes(self) -> list[FileDescriptor]:
        return sorted(
            [v for _, v in self.get_files().items() if v.kind == self.KINDS.mst],
            key=lambda fd: fd.basename,
            reverse=True,
        )

    def delete_card(self, i):
        self.active_file.data.drop([i], inplace=True, axis=0)
        self.active_file.data.reset_index(inplace=True, drop=True)

    @cache
    def match_from_all_languages(
        self, repat: re.Pattern, exclude_dirs: re.Pattern = re.compile(r".^")
    ) -> set[os.PathLike]:
        matching = set()
        for lng_rootdir in {
            d for d in os.listdir(self.DATA_PATH) if not exclude_dirs.search(d)
        }:
            for lng_file in {
                f
                for f in os.listdir(self.make_filepath(lng_rootdir, self.LNG_DIR))
                if repat.search(f)
            }:
                matching.add(self.make_filepath(lng_rootdir, self.LNG_DIR, lng_file))
        return matching

    def get_files_in_dir(self, path, include_extension=True, exclude_open=True):
        files_list = [
            f
            for f in os.listdir(path)
            if os.path.isfile(os.path.join(path, f)) and f not in {"desktop.ini"}
        ]
        if not include_extension:
            files_list = [f.split(".")[0] for f in files_list]
        if exclude_open:
            # exclude locks for open files for OS: Linux, Windows
            files_list[:] = [
                f
                for f in files_list
                if not any(f.startswith(tmp) for tmp in {"~$", ".~"})
            ]
        return files_list

    def get_all_languages(self) -> set:
        out = set()
        for d in os.listdir(self.DATA_PATH):
            if all(
                [
                    (kind in os.listdir(os.path.join(self.DATA_PATH, d)))
                    for kind in {k for k in dir(self.KINDS) if not k.startswith("__")}
                ]
            ):
                out.add(d)
        return out
