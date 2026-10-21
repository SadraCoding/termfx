from ._commands import main
import sys

try:
    sys.exit(main(sys.argv))
except KeyboardInterrupt:
    sys.exit(130)
