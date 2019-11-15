import ctypes
from queue import Queue
from threading import Thread
from time import sleep, clock
from collections import namedtuple

__author__ = 'Xuansheng Wu'
__version__ = '0.1.0'
__update__ = '2019-11-15'
__email__ = 'wuxsmail@163.com'


MIN_LUNCH_BREAK = 0.01 # the minimum lunch break of ThreadPool
MAX_RETRY_EXIT = 5
SYSTEM_EXIT = ctypes.py_object(SystemExit)

def _update_pool_info(pool, queue, work_time):
    while pool._working:
        if not pool._waiting:
            while not queue.empty():
                task = queue.get()
                del pool[task.id]
                work_time.append(task.time)
        sleep(MIN_LUNCH_BREAK)

ExistInfo = namedtuple('ExistInfo', ['id', 'time'])
def _task_callback_wrapper(task, queue, result):
    assert callable(task)
    def func(task_number, queue, *args, **kwrds):
        begin = clock()
        try:
            result.put(task(*args, **kwrds))
        finally:
            queue.put(ExistInfo(task_number, clock() - begin))
    func.__name__ = task.__name__
    return func

def _mean(values):
    return sum(values, 0.0) / len(values)


class Pool(dict):
    def __init__(self, max_size, task, args=(), kwrds={}):
        dict.__init__(self)
        self.max_size = max_size
        self._callback = Queue()
        self._result = Queue()
        self.set_task(task, *args, **kwrds)

        self._task_numbers = 1
        self._wait_time = []
        self._work_time = []
        self._daemon = None
        self._working = False
        self._waiting = False

    @property
    def result(self):
        return self._result

    @property
    def max_size(self):
        return self._max_size

    @max_size.setter
    def max_size(self, times):
        assert isinstance(times, int) and times >= 0
        self._max_size = times

    @property
    def constant_arguments(self):
        return self._args

    @property
    def constant_keywords(self):
        return self._kwrds

    @property
    def task(self):
        return self._task.__name__

    def set_task(self, new_task, *args, **kwrds):
        '''reset the task function and initial parameters'''
        assert callable(new_task), '`task` must be a callable object'
        self._task = _task_callback_wrapper(new_task,
                                            self._callback,
                                            self._result)
        self._args = args
        self._kwrds = kwrds

    def iter_results(self):
        '''return all finished results as an iterable object'''
        while not self._result.empty():
            yield self._result.get()

    def get_results(self):
        '''return all finished results as a list'''
        return list(self.iter_results())

    def __enter__(self):
        self._working = True
        self._daemon = Thread(target=_update_pool_info,
                              args=(self, self._callback, self._work_time))
        self._daemon.setDaemon(True)
        self._daemon.start()
        return self

    def __exit__(self, exc_type, exc_value, traceback, retry=MAX_RETRY_EXIT):
        for times in range(retry):
            for name, thread in self.items():
                tid = ctypes.c_long(thread.ident)
                ctypes.pythonapi.PyThreadState_SetAsyncExc(tid, SYSTEM_EXIT)
            if len(self) == 0:
                break
            sleep(MIN_LUNCH_BREAK)
        else:
            err = '%d threads failed to be killed after %d times retry'
            SystemError(err % (len(self), retry))
        self._working = False

    def open(self):
        '''start running (enable creating new thread) the Thread Pool'''
        self.__enter__(self)

    def close(self, retry=MAX_RETRY_EXIT):
        '''kill all alived threads and cannot create any new threads'''
        self.__exit__(None, None, None, retry)

    def _thread_block_full(self):
        waiting_time = 0.0
        while len(self) == self._max_size:
            sleep(MIN_LUNCH_BREAK)
            waiting_time += MIN_LUNCH_BREAK
        else:
            self._wait_time.append(waiting_time)

    def start(self, *args, **kwargs):
        '''launch a new worker'''
        assert self._daemon is not None, 'please run ThreadPool.open() at first'
        self._thread_block_full()
        
        self._task_numbers += 1
        args = (self._task_numbers, self._callback) + self._args + args        
        worker = Thread(target=self._task,
                        args=args,
                        kwargs=kwargs)
        self[self._task_numbers] = worker
        worker.start()

    def map(self, iter_params):
        '''launch multiple new workers with all parameters'''
        for params in iter_params:
            assert isinstance(params, tuple), 'arguments must be tuple'
            self.start(*params)

    def join(self, timeout=None):
        '''block the main thread until all workers done'''
        self._waiting = True
        for worker in self.values():
            worker.join(timeout)
        self._waiting = False

    def report(self):
        '''statistic information for this thread pool'''
        print(' - Threading Pool for task %s' % self._task.__name__)
        print('   * current Pool is Active: %s' % self._working)
        print('   * totally lunched %d threads' % (self._task_numbers - 1))
        print('   * current working %d threads' % len(self))
        print('   * average working time %.2f seconds' % _mean(self._work_time))
        print('   * average waiting time %.2f seconds' % _mean(self._wait_time))
