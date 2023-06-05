from lumensigner.controller import Controller


def start():
    # Get the one and only Controller instance and start our main loop
    Controller.get_instance().start()
