import os
from typing import Final

SIMULATE_MODE: Final = os.environ.get("LOCAL_DEV") == "true"
