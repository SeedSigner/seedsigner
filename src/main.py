import configparser
import sys
import time

from seedsigner.controller import Controller


config = configparser.ConfigParser()
config.read("settings.ini")

controller = Controller(config)
controller.start()
