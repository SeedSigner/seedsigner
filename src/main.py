import configparser
import sys
import time

from seedsigner.controller import Controller


config = configparser.ConfigParser()
config.read("settings.ini")

# One-time setup to intialize the one and only Controller
Controller.configure_instance(config)

# Get the one and only Controller instance and start our main loop
controller = Controller.get_instance()
controller.start()
