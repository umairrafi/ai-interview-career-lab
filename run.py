"""Run the hands-on session: python3 run.py"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "src"))

from ledgerlab.practice import main

if __name__ == "__main__":
    main()
