from seedsigner.controller import Controller

# Get the one and only Controller instance and start our main loop
controller = Controller.get_instance()

controller.start()
