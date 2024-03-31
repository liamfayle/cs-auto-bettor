import logging
from datetime import datetime
import os

# Log levels
LEVEL_STANDARD = 1
LEVEL_WARNING = 2
LEVEL_ERROR = 3

# Setting up the logger
def setup_logger():
    # Create a logs directory if it doesn't exist
    if not os.path.exists('logs'):
        os.makedirs('logs')

    # Filename based on current date
    filename = datetime.now().strftime("logs/log_%Y-%m-%d.txt")

    # Create and configure logger
    logger = logging.getLogger('CustomLogger')
    logger.setLevel(logging.DEBUG)  # Set to lowest level to capture all types of logs

    # Create file handler which logs even debug messages
    fh = logging.FileHandler(filename)
    fh.setLevel(logging.DEBUG)

    # Create formatter and add it to the handler
    formatter = logging.Formatter('[%(levelname)s] %(asctime)s: %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
    fh.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(fh)
    return logger

# Initialize the logger
_logger = setup_logger()

# Function to log messages
def log(message, level=LEVEL_STANDARD):
    if level == LEVEL_STANDARD:
        _logger.info(message)
    elif level == LEVEL_WARNING:
        _logger.warning(message)
    elif level == LEVEL_ERROR:
        _logger.error(message)

# Example usage
if __name__ == "__main__":
    log("This is a standard message")  # Default level
    log("This is a warning message", level=LEVEL_WARNING)
    log("This is an error message", level=LEVEL_ERROR)