import sys

from ._commands import main

try:
    sys.exit(main(sys.argv))
except KeyboardInterrupt:
    sys.exit(130)
