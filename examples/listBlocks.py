#!/usr/bin/env python

import snap7

client = snap7.client.Client()
client.connect("127.0.0.1", 0, 0, 102)

print client.list_blocks()
blocktype=snap7.types.block_types['DB']

for i in client.list_blocks_of_type(snap7.snap7types.block_types['DB']):
    print i
    
