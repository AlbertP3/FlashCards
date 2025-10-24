import logging
from dataclasses import dataclass, fields
from collections import deque
from time import perf_counter
from utils import singleton
from PyQt5.QtCore import pyqtSignal, QObject, QThreadPool, pyqtSlot, QRunnable, Qt, QObject
from cfg import config
from datetime import datetime
from typing import Optional as Opt, Callable
import threading


log = logging.getLogger("INT")


@singleton
class SignalBus(QObject):
    sfe_mod = pyqtSignal(int)
    fcc_queue_msg = pyqtSignal()
    efc_calc_job = pyqtSignal()


@dataclass
class LogLvl:
    debug: int = 0
    info: int = 1
    important: int = 2
    warn: int = 3
    err: int = 4
    exc: int = 5

    @staticmethod
    def get_fields() -> list[str]:
        return [field.name for field in fields(LogLvl)]

    @staticmethod
    def get_field_name_by_value(value: int) -> Opt[str]:
        for field in fields(LogLvl):
            if getattr(LogLvl, field.name) == value:
                return field.name


@dataclass
class QueueRecord:
    message: str
    timestamp: datetime
    lvl: int = LogLvl.debug
    func: Opt[Callable] = None


class FccQueue(QObject):
    """Collects messages to be displayed in the console"""

    def __init__(self):
        super().__init__()
        self.__fcc_queue: deque[QueueRecord] = deque()
        self.__notification_queue: deque[QueueRecord] = deque()
        self.unacked_notifications = 0

    def put_log(self, msg: str, log_func: Opt[Callable] = None):
        if msg:
            record = QueueRecord(
                message=msg,
                timestamp=datetime.now(),
            )
            self.__fcc_queue.append(record)
            if log_func:
                log_func(msg, stacklevel=2)

    def put_notification(
        self,
        msg: str,
        lvl: int = LogLvl.debug,
        func: Opt[Callable] = None,
    ):
        if msg and lvl >= config["popups"]["lvl"]:
            record = QueueRecord(
                message=msg,
                timestamp=datetime.now(),
                lvl=lvl,
                func=func,
            )
            self.__notification_queue.append(record)
            self.unacked_notifications += 1
            sbus.fcc_queue_msg.emit()

    def pull_log(self) -> QueueRecord:
        return self.__fcc_queue.popleft()

    def dump_logs(self) -> list[QueueRecord]:
        res = list(self.__fcc_queue)
        self.__fcc_queue.clear()
        return res

    def get_logs(self) -> list[QueueRecord]:
        return list(self.__fcc_queue)

    def pull_notification(self) -> QueueRecord:
        return self.__notification_queue.popleft()

    def get_notifications(self) -> list[QueueRecord]:
        return list(self.__fcc_queue)


class TaskSignals(QObject):
    task_started = pyqtSignal()
    task_finished = pyqtSignal()


class Task(QRunnable):

    def __init__(
        self,
        functions: list[Callable],
        op_id: str,
        started: Opt[Callable] = None,
        finished: Opt[list[Callable]] = None,
        auto_delete: bool = True,
    ):
        super().__init__()
        self.setAutoDelete(auto_delete)
        self.op_id = op_id
        self.signals = TaskSignals()

        self.fn = lambda: [f() for f in functions]

        if started:
            self.signals.task_started.connect(
                lambda: started(config.cache["load_est"].get(self.op_id, 2500)),
                Qt.QueuedConnection,
            )

        if finished:
            finished.append(self.__record_time)
        else:
            finished = [self.__record_time]
        self.signals.task_finished.connect(
            lambda: [f() for f in finished], Qt.QueuedConnection
        )

    def __record_time(self):
        config.cache["load_est"][self.op_id] = int(1000 * (perf_counter() - self.t0))

    @pyqtSlot()
    def run(self):
        self.t0 = perf_counter()
        self.signals.task_started.emit()
        self.fn()
        self.signals.task_finished.emit()


class ThreadTimer:
    def __init__(self, interval: float, func: Callable, *args, **kwargs):
        self.interval = interval
        self.func = func
        self.args = args
        self.kwargs = kwargs
        self._stop = threading.Event()
        self._thread = None

    def _run(self):
        while not self._stop.wait(self.interval):
            self.func(*self.args, **self.kwargs)

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._stop.set()


@dataclass
class Job:
    task: Task
    trigger: Callable
    enabled: bool = True


class Scheduler:
    def __init__(self):
        self.__pool = QThreadPool()
        self.__jobs: dict[int, Job] = {}
        self.__jobs_to_delete: set[str] = set()
        self.__clock = ThreadTimer(60 * config["scheduler_interval_m"], self.__monitor)

    @property
    def __active_jobs(self):
        for ident, job in self.__jobs.items():
            if job.enabled:
                yield (ident, job)

    def add_job(self, ident: str, task: Task, trigger: Callable):
        self.__jobs[ident] = Job(task, trigger)
        log.debug(f"Added job: {ident}")
        self.__clock.start()

    def enable_job(self, ident: str):
        self.__jobs[ident].enabled = True

    def disable_job(self, ident: str):
        self.__jobs[ident].enabled = False

    def delete_job(self, ident: str):
        self.__jobs_to_delete.add(ident)

    def run_job(self, ident: int):
        job = self.__jobs[ident]
        log.debug(f"Running job: {ident}")
        self.__pool.start(job.task)
        if job.task.autoDelete():
            self.__jobs[ident].enabled = False
            self.__jobs_to_delete.add(ident)

    def run_task(self, task: Task):
        log.debug(f"Running task: {task.op_id}")
        self.__pool.start(task)

    def __monitor(self):
        cnt = 0
        for ident, job in self.__active_jobs:
            if job.trigger():
                self.run_job(ident)
            cnt += 1
        if cnt == 0:
            self.__clock.stop()
            log.debug(f"No active jobs left. Stopped")
        self.__delete_jobs()

    def __delete_jobs(self):
        for ident in self.__jobs_to_delete:
            try:
                del self.__jobs[ident]
                log.debug(f"Removed job: {ident}")
            except KeyError:
                pass
        self.__jobs_to_delete.clear()


sbus = SignalBus()
fcc_queue = FccQueue()
sched = Scheduler()
