import sys
sys.path.append('./views')
sys.path.append('./models')
sys.path.append('./helpers')

from controller import Controller
import time

DEBUG = True

controller = Controller()
controller.start(DEBUG)