import configparser
import pytest
from mock import MagicMock
from seedsigner.controller import Controller



def test_singleton_init_fails():
	""" The Controller should not allow any code to instantiate it via Controller() """
	with pytest.raises(Exception):
		c = Controller()

def test_singleton_get_instance_without_configure_fails():
	""" Calling get_instance() without first calling configure_instance() should fail """
	with pytest.raises(Exception):
		c = Controller.get_instance()

def test_singleton_get_instance_preserves_state():
	""" Changes to the Controller singleton should be preserved across calls to get_instance() """
	settings = """
		[system]
		DEBUG = True
		DEFAULT_LANGUAGE = en

		[display]
		BACKGROUND_COLOR = #000
		TEXT_COLOR = orange
	"""
	config = configparser.ConfigParser()
	config.read_string(settings)

	# Initialize the instance and verify that it read the config settings
	Controller.configure_instance(config)
	controller = Controller.get_instance()
	assert controller.color == "orange"

	# Change a value in the instance...
	controller.color = "purple"

	# ...get a new copy of the instance and confirm change
	controller = Controller.get_instance()
	assert controller.color == "purple"
