# -*- coding: utf-8 -*-

import socket, select, threading

BIND_ADDRESS = '127.0.0.1'
STREAM_ADDRESS = BIND_ADDRESS
TIMEOUT = 30

class StreamServer():
    def __init__(self):
        pass

    def start(self, urls):
        #Create a stream server. 
        stream = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        stream.bind((BIND_ADDRESS, 0))
        stream.listen(1)
        port = stream.getsockname()[1]

        #Start to accepting
        threading.Thread(target = self.run, args = [stream]).start()
        return 'http://%s:%d' % (STREAM_ADDRESS, port)

    def run(self, stream):
        #Wait for connection
        readable, _, _ = select.select([stream], [], [], TIMEOUT)
        if not (readable):
            stream.close()
            return

        stream.setblocking(False)
        socks = [stream]

        while socks:
            readable, _, _ = select.select(socks, socks, socks)

            for s in readable:
                if s is stream:
                    #conn.close()
                    conn, _ = stream.accept()
                    conn.setblocking(False)
                    print 'Accept from ', conn.getpeername()
                    socks.append(conn)
                else:
                    data = s.recv(1500)
                    if data:
                        print 'Receive data (%d) from %s' % (len(data), s.getpeername())
                    else:
                        print 'Disconnect from ', s.getpeername()
                        socks.remove(s)
                        s.close()
                        if stream in socks:
                            socks.remove(stream)

        stream.close()

if __name__ == '__main__':
    urls = ["http://61.160.198.173/6775E110ADF4582C5666164999/0300010F00565D1FE3C56F2BEEFCF901BB750B-7814-8BB7-FAD0-3F9AB238B46E.flv.ts",
            "http://221.228.249.84/6574E6387AE3D8371AEDEC5EAF/0300010F01565D1FE3C56F2BEEFCF901BB750B-7814-8BB7-FAD0-3F9AB238B46E.flv.ts",
            "http://61.160.198.134/6979CC708983B825D1301E40A5/0300010F02565D1FE3C56F2BEEFCF901BB750B-7814-8BB7-FAD0-3F9AB238B46E.flv.ts",
            "http://222.73.61.242/697AC74868F49816539D2561EC/0300010F03565D1FE3C56F2BEEFCF901BB750B-7814-8BB7-FAD0-3F9AB238B46E.flv.ts",
            "http://202.102.93.180/6779CC70B5A31814585D232996/0300010F04565D1FE3C56F2BEEFCF901BB750B-7814-8BB7-FAD0-3F9AB238B46E.flv.ts",
            "http://222.73.245.131/677AC74852B4E81817BEAB4731/0300010F05565D1FE3C56F2BEEFCF901BB750B-7814-8BB7-FAD0-3F9AB238B46E.flv.ts",
            "http://222.73.61.210/6579CC7054146815656DF85210/0300010F06565D1FE3C56F2BEEFCF901BB750B-7814-8BB7-FAD0-3F9AB238B46E.flv.ts",
            "http://61.160.227.19/677DB7D08314382B0FE28E3C22/0300010F08565D1FE3C56F2BEEFCF901BB750B-7814-8BB7-FAD0-3F9AB238B46E.flv.ts",
            "http://222.73.61.235/69810A858A4A4A816A2FD5463A3/0300010F09565D1FE3C56F2BEEFCF901BB750B-7814-8BB7-FAD0-3F9AB238B46E.flv.ts",
            "http://202.102.88.215/69811A330B464581CD1393E4914/0300010F0A565D1FE3C56F2BEEFCF901BB750B-7814-8BB7-FAD0-3F9AB238B46E.flv.ts",
            "http://61.160.198.85/698129E08EF6368228E902C6E40/0300010F0B565D1FE3C56F2BEEFCF901BB750B-7814-8BB7-FAD0-3F9AB238B46E.flv.ts",
            "http://222.73.61.182/657FAD805D24581516047A31C6/0300010F0C565D1FE3C56F2BEEFCF901BB750B-7814-8BB7-FAD0-3F9AB238B46E.flv.ts",
            "http://221.228.249.85/678129E087E04B843F68C20255E/0300010F0D565D1FE3C56F2BEEFCF901BB750B-7814-8BB7-FAD0-3F9AB238B46E.flv.ts",
            "http://101.226.184.18/6781398E058F498417DF62560F8/0300010F0E565D1FE3C56F2BEEFCF901BB750B-7814-8BB7-FAD0-3F9AB238B46E.flv.ts"]
    ss = StreamServer()
    url = ss.start(urls)
    print(url)
