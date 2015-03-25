import snap7
import os
from plc import db_layouts

db = 300
file = os.path.join(os.path.dirname(os.path.abspath(os.path.curdir)), 'data', 'dbdump', str(db) + '.db')

data = bytearray(open(file, 'rb').read())
#print data

dbVarName = 'db' + str(db)
layout = getattr(db_layouts, dbVarName)

parsed = snap7.util.DB(db, data, layout) # this was ok
print repr(parsed)