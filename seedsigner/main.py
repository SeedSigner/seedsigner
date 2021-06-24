import configparser
import sys
import time

sys.path.append('./views')
sys.path.append('./models')
sys.path.append('./helpers')

from controller import Controller


config = configparser.ConfigParser()
config.read("settings.ini")

controller = Controller(config)
controller.start()
