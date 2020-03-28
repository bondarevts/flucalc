import math
import multiprocessing as mp
import logging


def calc_min_power(*values):
    return int(min(math.floor(math.log10(value)) for value in values))


def format_number_with_power(number, power, precision=4):
    return '{0:.{1}f}e{2:+03d}'.format(number / pow(10, power), precision, power)


def run_parallel(func, args=(), kwargs=None, timeout=None):
    if kwargs is None:
        kwargs = {}

    ctx = mp.get_context('spawn')
    out_pipe, in_pipe = ctx.Pipe(duplex=False)
    process = ctx.Process(target=apply_function_to_pipe, args=(func, args, kwargs, in_pipe))
    process.daemon = True
    process.start()
    logging.info('Process started')
    logging.info('Run calculation in process %s', process.pid)
    process.join(timeout=timeout)
    if not process.is_alive():
        logging.info('Calculation finished')
        return out_pipe.recv()

    logging.info('Try to terminate process')
    process.terminate()
    logging.info('Calculation terminated by timeout')
    raise mp.TimeoutError


def apply_function_to_pipe(func, args, kwargs, pipe):
    try:
        pipe.send(func(*args, **kwargs))
    except Exception:
        logging.exception('Processing error')
