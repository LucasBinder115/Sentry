import logging

def get_logger(name):
    logger = logging.getLogger(name)
    # Configura handlers, format, etc.
    return logger