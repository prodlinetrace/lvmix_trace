#!flask/bin/python
import os
import sys
if sys.platform == 'wiin32':
    pybabel = 'pybabel.exe'
else:
    pybabel = 'pybabel'
os.system(pybabel + ' extract -F babel.cfg -k gettext -o messages.pot .')
os.system(pybabel + ' update -i messages.pot -d locale')
#os.unlink('messages.pot')
