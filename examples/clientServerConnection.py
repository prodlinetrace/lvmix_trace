import snap7
import time

server = snap7.server.Server()
client = snap7.client.Client()
print "server status", server.get_status()
print "client status", client.get_connected()
server.start_to("0.0.0.0", tcpport=1102)

client.connect("127.0.0.1", 0, 2, 1102)
print "server status", server.get_status()
print "client status", client.get_connected()
time.sleep(1)
print "done. disconnect"
