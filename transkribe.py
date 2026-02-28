"""Legacy entry point — delegates to the stt package.

Use 'python -m stt <audio_file>' instead.
"""

import sys

from stt.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
