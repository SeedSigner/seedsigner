from threading import Event
import time
from seedsigner.models.threads import T, BaseThread, ThreadsafeVar



class SimpleThreadTester(BaseThread):
    def __init__(self, threadsafe_var: ThreadsafeVar[T] = None, exit_when_equal: T = None):
        super().__init__()
        self.threadsafe_var = threadsafe_var
        self.exit_when_equal = exit_when_equal
    

    def run(self):
        while not self.event.wait(timeout=0.1):
            if self.threadsafe_var.cur_value == self.exit_when_equal:
                break            
        
        print("Thread exiting itself")



class TestThreadClass:
    def test_thread_event_exit(self):
        threadsafe_var = ThreadsafeVar[int]()
        exit_when_equal = 100
        test_thread = SimpleThreadTester(threadsafe_var=threadsafe_var, exit_when_equal=exit_when_equal)
        test_thread.start()

        assert test_thread.is_alive()

        # Now signal the thread to cancel itself
        test_thread.stop()
        test_thread.join()
        assert not test_thread.is_alive()



class TestThreadsafeVar:
    def test_threadsafevar_generic_type_get_set(self):
        threadsafe_var = ThreadsafeVar[int]()
        assert threadsafe_var.cur_value is None
        threadsafe_var.set_value(21)
        assert threadsafe_var.cur_value == 21

        threadsafe_var = ThreadsafeVar[bool]()
        assert threadsafe_var.cur_value is None
        threadsafe_var.set_value(True)
        assert threadsafe_var.cur_value is True

        threadsafe_var = ThreadsafeVar[str]()
        assert threadsafe_var.cur_value is None
        threadsafe_var.set_value("satoshi")
        assert threadsafe_var.cur_value is "satoshi"


    def test_threadsafevar_int(self):
        threadsafe_var = ThreadsafeVar[int]()
        exit_when_equal = 10
        test_thread = SimpleThreadTester(threadsafe_var=threadsafe_var, exit_when_equal=exit_when_equal)
        test_thread.start()

        while not test_thread.is_alive():
            time.sleep(0.1)

        for i in range(1, exit_when_equal):
            threadsafe_var.set_value(i)
            assert threadsafe_var.cur_value != exit_when_equal
            assert test_thread.is_alive()

        threadsafe_var.set_value(exit_when_equal)
        assert threadsafe_var.cur_value == exit_when_equal

        # Give the thread a moment to end itself
        test_thread.join()

        assert not test_thread.is_alive()


    def test_threadsafevar_bool(self):
        threadsafe_var = ThreadsafeVar[bool]()
        exit_when_equal = True
        test_thread = SimpleThreadTester(threadsafe_var=threadsafe_var, exit_when_equal=exit_when_equal)
        test_thread.start()

        threadsafe_var.set_value(False)
        assert test_thread.is_alive()

        threadsafe_var.set_value(exit_when_equal)

        # Give the thread a moment to end itself
        test_thread.join()

        assert not test_thread.is_alive()
        