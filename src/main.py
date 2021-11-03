import logging
import configparser

from seedsigner.controller import Controller
from seedsigner.helpers import configure_logging


config = configparser.ConfigParser()
config.read("settings.ini")

configure_logging(config["system"].get("log_file", "debug.log"))

logging.debug("Configurations loaded")

# One-time setup to intialize the one and only Controller
Controller.configure_instance(config)

# Get the one and only Controller instance and start our main loop
controller = Controller.get_instance()
controller.start()
