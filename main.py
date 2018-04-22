import sys
import logging
import traceback
import zmq
import cv2

from PyQt5.QtCore import *  # crashes if not generic
from PyQt5.QtGui import *
from PyQt5.QtWidgets import QMainWindow, QSizePolicy, QHeaderView, QFileSystemModel, QMessageBox, QMenu, QAction, \
    QLabel, QProgressBar, QDialog, QTableView, QButtonGroup, QFileDialog

from MainWindow import *

class Controller(QMainWindow, Ui_MainWindow):

    def __init__(self):
        super().__init__()
        self.setupUi(self)


def handle_uncaugth_exception(*exc_info):
    """
    This function will be subsituted to sys.except_hook standard function that is raised when ecxeptions are raised and
    not caugth by some try: except: block
    :param exc_info: (exc_type, exc_value, exc_traceback)
    :return: stop program with return code 1
    """
    stack = traceback.extract_stack()[:-3] + traceback.extract_tb(exc_info[1].__traceback__)  # add limit=??
    pretty = traceback.format_list(stack)
    text = ''.join(pretty) + '\n  {} {}'.format(exc_info[1].__class__, exc_info[1])
    # text = "".join(traceback.format_exception(*exc_info))
    logger.error("Unhandled exception: %s", text)
    sys.exit(1)
    
if __name__ == "__main__":
    # set-up logger before anything - two  handlers : one on console, the other one on file
    formatter = \
        logging.Formatter("%(asctime)s :: %(funcName)s :: %(levelname)s :: %(message)s")

    handler_file = logging.FileHandler("video.log", mode="a", encoding="utf-8")
    handler_console = logging.StreamHandler()

    handler_file.setFormatter(formatter)
    handler_console.setFormatter(formatter)

    handler_file.setLevel(logging.DEBUG)
    handler_console.setLevel(logging.DEBUG)

    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)  # A D A P T   LOGGING LEVEL        H E R E
    logger.addHandler(handler_file)
    logger.addHandler(handler_console)

    sys.excepthook = handle_uncaugth_exception  # reassign so that log is fed with problem

    VERSION = "V0.0.1"
    PROGRAM_NAME = "VIDEO_DISPLAY"



    logger.info('=========  ' + PROGRAM_NAME + ' ' + VERSION + ' STARTED ===========')


    try:
        app = QtWidgets.QApplication(sys.argv)
        ui = Controller()
        ui.show()
        sys.exit(app.exec_())
    except Exception:
        logger.exception("Exception caugth:")

