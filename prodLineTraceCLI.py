#!/usr/bin/env python
import logging
import sys
from prodline import ProdLine
logger = logging.getLogger(__name__.ljust(12)[:12])


def main():
    logger.info("Starting main app")
    #sys.argv.append("-v")
    app = ProdLine(sys.argv)
    app.main()

if __name__ == "__main__":
    sys.exit(main())
