import time
import logging
from seedsigner.models.threads import BaseThread

def test_basethread_crash_handling(caplog):
    
    # This simulates a background process (like hardware listener or scroll ui)
    # breaking unexpectedly.
    class ExplodingThread(BaseThread):
        def run(self):
            raise ValueError("Intentional Crash!")

    with caplog.at_level(logging.ERROR):
        t = ExplodingThread()
        t.start()
        
        time.sleep(0.1)

        assert getattr(t, 'keep_running', True) is False
        
        assert "Thread ExplodingThread crashed: Intentional Crash!" in caplog.text
