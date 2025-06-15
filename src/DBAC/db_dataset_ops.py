import re
import random
import logging
import pandas as pd
import openpyxl
from datetime import datetime
from dataclasses import dataclass
import os
import csv
from utils import fcc_queue, LogLvl, translate
from cfg import config

log = logging.getLogger("DBA")


@dataclass
class FileDescriptor:
    basename: str = None
    filepath: str = None
    lng: str = None
    kind: str = "U"
    ext: str = None  # [.csv, .xlsx, ...]
    valid: bool = None
    data: pd.DataFrame = None
    signature: str = None
    tmp: bool = False
    parent: dict = None  # {filepath: str, len_: int}

    def __eq__(self, __value: object) -> bool:
        return self.filepath == __value.filepath


class DbDatasetOps:
    def __init__(self):
        self.empty_df = pd.DataFrame(data=[["-", "-"]])
        self.__AF = FileDescriptor(tmp=True, data=self.empty_df)
        self.__nsre = re.compile(r"(\d+)")

    @property
    def active_file(self):
        return self.__AF

    @active_file.setter
    def active_file(self, fd: FileDescriptor):
        self.validate_dataset(fd)
        if not fd.valid:
            fd.data = self.empty_df
            fd.tmp = True
            fd.kind = self.KINDS.unk
        if self.__AF != fd:
            # Clear stored data for previous active file
            self.__AF.data = None
        self.__AF = fd
        log.debug(
            (
                f"Activated {'Valid' if self.__AF.valid else 'Invalid'} "
                f"{'Temporary' if self.__AF.tmp else 'Regular'} "
                f"{self.KFN[self.__AF.kind]}: {self.__AF.filepath}"
            ),
            stacklevel=3,
        )
        if (
            len(d := {f.basename for f in self.files.values() if f.data is not None})
            > 1
        ):
            log.warning(f"There are {len(d)} FileDescriptors with data: {d}")

    def make_filepath(self, lng: str, kind: str, filename: str = "") -> str:
        """Template for creating Paths"""
        return os.path.join(self.DATA_PATH, lng, kind, filename)

    def gen_signature(self, language) -> str:
        """Create a globally unique identifier. Uses a custom pattern if available."""
        if base := config["sigenpat"].get(language):
            all_filenames = self.get_all_files(use_basenames=True, excl_ext=True)
            for i in range(1, 1001):
                tmp = f"{base}{i}"
                if tmp not in all_filenames:
                    return tmp
            else:
                fcc_queue.put_notification(
                    "Failed to generate a signature using the custom pattern",
                    lvl=LogLvl.warn,
                )
        saving_date = datetime.now().strftime("%d%m%Y%H%M%S")
        signature = f"REV_{language}{saving_date}"
        return signature

    def create_revision_file(self, dataset: pd.DataFrame) -> str:
        """Creates a new file for the Revision. Returns a new filepath"""
        try:
            fp = self.make_filepath(
                self.active_file.lng, self.REV_DIR, f"{self.active_file.signature}.csv"
            )
            dataset.to_csv(fp, index=False, encoding="utf-8")
            fcc_queue.put_notification(
                f"Created {self.active_file.signature}", lvl=LogLvl.important
            )
            log.info(f"Created a new file: {fp}")
            self.update_fds()
            return fp
        except Exception as e:
            fcc_queue.put_notification(
                f"Exception while creating a file: {e}. See log file for more details",
                lvl=LogLvl.exc,
            )
            log.error(e, exc_info=True)

    def create_mistakes_file(self, mistakes_list: list):
        """Dump, partition and rotate dataset to the Mistakes files"""
        name_fmt = self.MST_BASENAME.format(lng=self.active_file.lng)
        mfd = FileDescriptor(
            basename=f"{name_fmt}1.csv",
            filepath=self.make_filepath(
                self.active_file.lng, self.MST_DIR, f"{name_fmt}1.csv"
            ),
            lng=self.active_file.lng,
            kind=self.KINDS.mst,
            ext=".csv",
        )
        if mfd.filepath in self.files.keys():
            mst_1 = self.get_data(mfd)
            mst_new = pd.DataFrame(data=mistakes_list, columns=mst_1.columns)
            buffer = pd.concat([mst_1, mst_new], ignore_index=True)
        else:  # create a new mistakes file
            buffer = pd.DataFrame(
                data=mistakes_list, columns=self.active_file.data.columns
            )
        self.partition_mistakes_data(buffer)
        self.update_fds()
        m_cnt = len(mistakes_list)
        config["mst"]["unreviewed"] += m_cnt
        msg = f'{m_cnt} card{"s" if m_cnt>1 else ""} saved to Mistakes'
        fcc_queue.put_notification(msg, lvl=LogLvl.info)
        log.info(msg)

    def partition_mistakes_data(self, buffer: pd.DataFrame):
        """Partition new mistakes into file(s) with rotation"""
        name_fmt = self.MST_BASENAME.format(lng=self.active_file.lng)
        mst_1 = self.make_filepath(
            self.active_file.lng, self.MST_DIR, f"{name_fmt}1.csv"
        )
        part_size = config["mst"]["part_size"]
        parts = [
            buffer.iloc[i : i + part_size] for i in range(0, len(buffer), part_size)
        ]
        for i, part in enumerate(parts):
            part.to_csv(mst_1, index=False, mode="w", header=True)
            if i + 1 < len(parts):
                self.rotate_mistakes_files()

        log.debug(f"Partitioned Mistakes files for {self.active_file.lng}")

    def rotate_mistakes_files(self):
        """Rotates CSV files with a base name and a numbered suffix"""
        name_fmt = self.MST_BASENAME.format(lng=self.active_file.lng)
        max_count = config["mst"]["part_cnt"]

        # Delete the oldest file if it exceeds the max count
        oldest_file = self.make_filepath(
            self.active_file.lng, self.MST_DIR, f"{name_fmt}{max_count}.csv"
        )
        if os.path.exists(oldest_file):
            os.remove(oldest_file)

        # Shift files
        for i in range(max_count - 1, 0, -1):
            src = self.make_filepath(
                self.active_file.lng, self.MST_DIR, f"{name_fmt}{i}.csv"
            )
            dest = self.make_filepath(
                self.active_file.lng, self.MST_DIR, f"{name_fmt}{i+1}.csv"
            )
            if os.path.exists(src):
                os.rename(src, dest)

        # Remove excess files (after config change)
        i = max_count + 1
        while True:
            excess_file = self.make_filepath(
                self.active_file.lng, self.MST_DIR, f"{name_fmt}{i}.csv"
            )
            if os.path.exists(excess_file):
                os.remove(excess_file)
                i += 1
            else:
                break

        log.debug(f"Rotated Mistakes files for {self.active_file.lng}")

    def create_tmp_file_backup(self):
        self.active_file.data.to_csv(
            self.TMP_BACKUP_PATH, index=False, mode="w", header=True
        )
        config.cache["snapshot"]["file"] = {
            "filepath": self.TMP_BACKUP_PATH,
            "kind": self.active_file.kind,
            "basename": self.active_file.basename,
            "lng": self.active_file.lng,
            "parent": self.active_file.parent,
            "signature": self.active_file.signature,
        }
        log.debug(f"Created a temporary backup file at {self.TMP_BACKUP_PATH}")

    def validate_dataset(self, fd: FileDescriptor) -> bool:
        if not isinstance(fd.data, pd.DataFrame):
            fd.valid = False
            fcc_queue.put_notification(
                f"Invalid data: expected DataFrame, got {type(fd.data).__name__}",
                lvl=LogLvl.err,
            )
        else:
            if fd.data.shape[1] == 2:
                fd.valid = True
            else:
                fd.valid = False
                fcc_queue.put_notification(
                    f"Invalid data: expected 2 columns, got {fd.data.shape[1]}",
                    lvl=LogLvl.err,
                )
        return fd.valid

    def afops(
        self,
        fd: FileDescriptor,
        shuffle: bool = False,
        seed: int = None,
    ):
        fd.data = self.get_data(fd)

        if fd != self.active_file:
            self.active_file = fd

        if shuffle or seed:
            self.shuffle_dataset(fd, seed)

    def get_data(self, fd: FileDescriptor) -> pd.DataFrame:
        err_msg = ""
        _data = self.empty_df
        try:
            if fd.ext in {".csv", ".txt"}:
                _data = self.read_csv(fd.filepath)
            elif fd.ext in {".xlsx", ".xlsm"}:
                _data = self.read_excel(fd.filepath)
            elif fd.tmp:
                raise FileNotFoundError
            else:
                err_msg = f"Chosen extension is not (yet) supported: {fd.ext}"
        except FileNotFoundError as e:
            err_msg = f"File Not Found: {fd.filepath}"
            log.error(err_msg, exc_info=True)
        except Exception as e:
            err_msg = f"Exception occurred: {e}"
            log.error(e, exc_info=True)

        fcc_queue.put_notification(err_msg, lvl=LogLvl.err)
        return _data

    def get_lines_count(self, fd: FileDescriptor) -> int:
        if fd.ext in {".csv", ".txt"}:
            with open(fd.filepath, "rb") as f:
                cnt = (
                    sum(
                        buffer.count(b"\n")
                        for buffer in iter(lambda: f.read(1024 * 1024), b"")
                    )
                    - 1
                )
        elif fd.ext in {".xlsx", ".xlsm"}:
            workbook = openpyxl.load_workbook(
                fd.filepath, read_only=True, data_only=True
            )
            cnt = workbook.active.max_row - 1
        elif fd.tmp:
            cnt = fd.data.shape[0]
        else:
            raise FileExistsError(f"Unsupported file format: {fd.ext}")
        return cnt

    def load_tempfile(
        self,
        data: pd.DataFrame,
        kind: str,
        basename: str,
        lng: str,
        parent: dict,
        signature=None,
    ):
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
            parent=parent,
        )
        log.debug(f"Mocked a temporary file: {fd.basename}")
        self.active_file = fd

    def shuffle_dataset(self, fd: FileDescriptor, seed=None):
        if seed:
            pd_random_seed = config["pd_random_seed"]
        else:
            pd_random_seed = random.randrange(10000)
        config.update({"pd_random_seed": pd_random_seed})
        fd.data = fd.data.sample(frac=1, random_state=pd_random_seed).reset_index(
            drop=True
        )

    def read_csv(self, file_path) -> pd.DataFrame:
        dataset = pd.read_csv(
            file_path,
            encoding="utf-8",
            dtype=str,
            sep=(
                self.get_dialect(file_path)
                if translate(str(config["csv_sniffer"]))
                else ","
            ),
            index_col=False,
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
                delimiters=translate(str(config["csv_sniffer"])),
            )
            .delimiter
        )

    def read_excel(self, file_path):
        return pd.read_excel(
            file_path,
            sheet_name=0,
            dtype=str,
            index_col=False,
            engine="openpyxl",
            usecols=(0, 1),
            engine_kwargs={"data_only": True},
        )

    def update_fds(self) -> None:
        """Finds files matching active Languages"""
        self.files: dict[str, FileDescriptor] = dict()
        for lng in config["languages"]:
            self.__update_files(lng, self.REV_DIR, kind=self.KINDS.rev)
            self.__update_files(lng, self.LNG_DIR, kind=self.KINDS.lng)
            self.__update_files(lng, self.MST_DIR, kind=self.KINDS.mst)
        log.debug(
            f"Collected FileDescriptors for {len(self.files)} files", stacklevel=2
        )

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
        fcc_queue.put_notification(
            f"Created a directory tree for {lng}", lvl=LogLvl.important
        )
        log.info(f"Created a directory tree for {lng}")

    def nat_sort(self, s: str):
        return [
            (int(text) if text.isdigit() else text.lower())
            for text in self.__nsre.split(s)
        ]

    def get_sorted_revisions(self) -> list[FileDescriptor]:
        return sorted(
            [v for _, v in self.files.items() if v.kind == self.KINDS.rev],
            key=lambda fd: self.nat_sort(fd.basename),
            reverse=False,
        )

    def get_sorted_languages(self) -> list[FileDescriptor]:
        return sorted(
            [v for _, v in self.files.items() if v.kind == self.KINDS.lng],
            key=lambda fd: self.nat_sort(fd.basename),
            reverse=False,
        )

    def get_sorted_mistakes(self) -> list[FileDescriptor]:
        return sorted(
            [v for _, v in self.files.items() if v.kind == self.KINDS.mst],
            key=lambda fd: self.nat_sort(fd.basename),
            reverse=False,
        )

    def delete_card(self, i):
        self.active_file.data.drop([i], inplace=True, axis=0)
        self.active_file.data.reset_index(inplace=True, drop=True)

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
            # exclude locks for: Linux, Windows
            files_list[:] = [
                f
                for f in files_list
                if not any(f.startswith(tmp) for tmp in {"~$", ".~"})
            ]
        return files_list

    def get_all_files(
        self, dirs: set = None, use_basenames=False, excl_ext=False
    ) -> set[str]:
        """Returns files for all languages"""
        out = set()
        dirs = dirs or {self.REV_DIR, self.LNG_DIR, self.MST_DIR}
        for lng in os.listdir(self.DATA_PATH):
            try:
                for kind in dirs:
                    for f in os.listdir(os.path.join(self.DATA_PATH, lng, kind)):
                        fp = os.path.join(os.path.join(self.DATA_PATH, lng, kind, f))
                        if os.path.isfile(fp) and not f.startswith("__"):
                            out.add(fp)
            except FileNotFoundError:
                pass
        if use_basenames:
            out = {os.path.basename(f) for f in out}
        if excl_ext:
            out = {os.path.splitext(f)[0] for f in out}
        return out

    def get_available_languages(self, ignore: set = {"arch"}) -> set[str]:
        return {lng for lng in os.listdir(self.DATA_PATH) if lng not in ignore}
