import logging


def init_logger():
    handler = logging.StreamHandler()
    log_format = u'%(asctime)s [%(levelname)-1s %(process)d %(threadName)s]  %(message)s'
    handler.setFormatter(logging.Formatter(log_format))
    logger.addHandler(handler)
    logger.setLevel(logging.INFO)


logger = logging.getLogger("State-Machine")
init_logger()
