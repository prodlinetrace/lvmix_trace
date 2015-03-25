#!/usr/bin/env python
import logging
import sys
from plc.prodline import ProdLine


def main():
    logging.info("running main app")
    # sys.argv.append("-v")
    app = ProdLine(sys.argv)
    app.main()

if __name__ == "__main__":
    sys.exit(main())
