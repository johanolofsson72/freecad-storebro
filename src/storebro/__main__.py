"""`python -m storebro` entry point — delegates to :func:`storebro.cli.main`."""

import sys

from storebro.cli import main

if __name__ == "__main__":
    sys.exit(main())
