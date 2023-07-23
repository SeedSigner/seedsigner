from time import time
master_start = time()


start = time()
from seedsigner.controller import Controller
print("main.py time elapsed to import Controller:", time() - start)

# Get the one and only Controller instance and start our main loop
start = time()
controller = Controller.get_instance()
print("main.py time elapsed to import and initialize Controller:", time() - start)

print("*" * 80)
print("\nmain.py OVERALL time elapsed until Controller.start():", time() - master_start)
print("\n" + "*" * 80)
controller.start()
