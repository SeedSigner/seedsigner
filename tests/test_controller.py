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
		debug = False
		default_language = en
		persistent_settings = False
		
		[display]
		text_color = ORANGE
		
		[wallet]
		network = main
		software = Prompt
		qr_density = 2
		script_policy = PKWSH
		custom_derivation_enabled = False
		custom_derivation = m/0/0
	"""
	config = configparser.ConfigParser()
	config.read_string(settings)

	# Initialize the instance and verify that it read the config settings
	Controller.configure_instance(config)
	controller = Controller.get_instance()
	assert controller.color == "ORANGE"

	# Change a value in the instance...
	controller.color = "purple"

	# ...get a new copy of the instance and confirm change
	controller = Controller.get_instance()
	assert controller.color == "purple"
