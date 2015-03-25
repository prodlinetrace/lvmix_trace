#!/usr/bin/env python
import sys, os
pp = os.path.dirname(os.path.abspath(os.curdir))
sys.path.append(pp)
from plc.prodline import ProdLineBase


def main():
    sys.argv.append("-c../plcplus.conf")
    modulepath = ""
    print modulepath
    
    
    app = ProdLineBase(sys.argv)
    print "get the configuration"
    print app.getConfig()
    
    

if __name__ == "__main__":
    sys.exit(main())
