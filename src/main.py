from time import time
master_start = time()


start = time()
from seedsigner.controller import Controller
print("main.py time elapsed to import Controller:", time() - start)
# Get the one and only Controller instance and start our main loop
controller = Controller.get_instance()
print("main.py time elapsed to import and initialize Controller:", time() - start)


start = time()
from seedsigner.models.threads import BaseThread
class BackgroundImportThread(BaseThread):
    def run(self):
        start = time()
        from importlib import import_module

        # import seedsigner.hardware.buttons # slowly imports GPIO along the way

        def time_import(module_name):
            last = time()
            import_module(module_name)
            print(time() - last, module_name)

        time_import('embit')
        time_import('seedsigner.helpers.embit_utils')

        # Do costly initializations
        time_import('seedsigner.models.seed_storage')
        from seedsigner.models.seed_storage import SeedStorage
        Controller.get_instance().storage = SeedStorage()

        # Get MainMenuView ready to respond quickly
        time_import('seedsigner.views.scan_views')

        time_import('seedsigner.views.seed_views')

        time_import('seedsigner.views.tools_views')

        time_import('seedsigner.views.settings_views')

        # Lowest priority costly initializations
        # time_import('picamera')
        # time_import('picamera.array')
        # time_import('seedsigner.hardware.pivideostream')

        print("Total BackgroundImportThread import time:", time() - start)

        exit()
background_import_thread = BackgroundImportThread()
background_import_thread.start()
print("main.py time elapsed through BackgroundImportThread.start():", time() - start)


print("*" * 80)
print("\nmain.py OVERALL time elapsed until Controller.start():", time() - master_start)
print("\n" + "*" * 80)
controller.start()
