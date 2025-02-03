from datetime import date
from itertools import chain
from dataclasses import dataclass, field
from collections import OrderedDict

IMM_CATS = ("wrt", "rdg", "lst", "spk", "ent")


@dataclass
class SubRecord:
    lessons: int = 0
    hours: int = 0
    hours_new: int = 0
    positives: int = 0
    total: int = 0

    def __add__(self, val):
        return SubRecord(
            lessons=self.lessons + val.lessons,
            hours=self.hours + val.hours,
            hours_new=self.hours_new + val.hours_new,
            positives=self.positives + val.positives,
            total=self.total + val.total,
        )


@dataclass
class Record:
    duo: SubRecord = field(default_factory=SubRecord)
    fcs: SubRecord = field(default_factory=SubRecord)
    wrt: SubRecord = field(default_factory=SubRecord)
    rdg: SubRecord = field(default_factory=SubRecord)
    lst: SubRecord = field(default_factory=SubRecord)
    spk: SubRecord = field(default_factory=SubRecord)
    ent: SubRecord = field(default_factory=SubRecord)

    def __add__(self, val):
        return Record(
            duo=self.duo + val.duo,
            fcs=self.fcs + val.fcs,
            wrt=self.wrt + val.wrt,
            rdg=self.rdg + val.rdg,
            lst=self.lst + val.lst,
            spk=self.spk + val.spk,
            ent=self.ent + val.ent,
        )

    @property
    def total_hours(self) -> float:
        return (
            self.duo.hours
            + self.fcs.hours
            + self.wrt.hours
            + self.rdg.hours
            + self.lst.hours
            + self.spk.hours
            + self.ent.hours
        )

    @property
    def total_hours_new(self) -> float:
        return (
            self.duo.hours_new
            + self.fcs.hours_new
            + self.wrt.hours_new
            + self.rdg.hours_new
            + self.lst.hours_new
            + self.spk.hours_new
            + self.ent.hours_new
        )


class Column:
    def __init__(self, cells: list[list[str]], filler=" "):
        self.__flat = list(chain.from_iterable(cells))
        self.__width = max(len(i) for i in self.__flat)
        self.__filler = filler

    def __getitem__(self, index: int):
        try:
            return self.__flat[index].ljust(self.__width, self.__filler)
        except IndexError:
            return self.__filler.ljust(self.__width, self.__filler)

    def __len__(self) -> int:
        return len(self.__flat)


RecordOrderedDict = OrderedDict[date, Record]
StrRecordOrderedDict = OrderedDict[str, Record]
