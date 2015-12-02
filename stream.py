# -*- coding: utf-8 -*-

import socket, select, threading, urllib2

BIND_ADDRESS = '0.0.0.0'
STREAM_ADDRESS = '127.0.0.1'
TIMEOUT = 5
MSS = 1440

class StreamServer():
    def __init__(self):
        pass

    def getSizes(self, urls):
        infos = []
        threads = []

        #Get header concurrently. 
        for url in  urls:
            infos.append([])
            t = threading.Thread(target = self.getInfo, args = [url, infos[-1]])
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        if len(infos) == 0:
            return [], ''

        sizes = []
        for info in infos:
            if len(info) == 0:
                return [], ''
            sizes.append(int(info[0]['content-length']))

        return sizes, infos[0][0]['content-type']

    def getInfo(self, url, info):
        #Get header
        request = urllib2.Request(url)
        request.get_method = lambda : 'HEAD'
        response = urllib2.urlopen(request)

        #Check return code
        if response.getcode() == 200:
            info.append(response.info())


    def start(self, urls):
        #Create a stream server. 
        server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        server.bind((BIND_ADDRESS, 0))
        server.listen(1)
        server.setblocking(False)
        port = server.getsockname()[1]

        #Get sizes
        sizes, content_type = self.getSizes(urls)

        #Start to accepting
        threading.Thread(target = self.run, args = [server, sizes, content_type]).start()
        return 'http://%s:%d' % (STREAM_ADDRESS, port)

    def processHEAD(self, stream, content_type, content_length):
        #Send response to HEAD request
        stream.send('HTTP/1.1 200 OK\r\n'
                   'Content-Type: %s\r\n'
                   'Accept-Ranges: bytes\r\n'
                   'Content-Length: %d\r\n'
                   'Connection: close\r\n\r\n' % (content_type, content_length))

    def run(self, server, sizes, content_type):
        #Calculate the total size
        total_size = 0
        for size in  sizes:
            total_size += size

        stream = None
        agent = None
        inputs = [server]

        while True:
            readable, _, _ = select.select(inputs, [], [], TIMEOUT)

            #Check timeouts
            if not readable and len(inputs) == 1:
                server.close()
                return

            if server in  readable:
                #New connection from client. Close previous connection. 
                if stream in inputs:
                    inputs.remove(stream)
                    stream.close()
                    stream = None
                stream, _ = server.accept()
                stream.setblocking(False)
                print 'Accept from ', stream.getpeername()
                inputs.append(stream)

            if stream in readable:
                #Data from client
                try:
                    data = stream.recv(MSS)
                    if not data:
                        raise
                    print 'Receive data (%d) from %s' % (len(data), stream.getpeername())
                    if data[:4].upper() == 'HEAD':
                        self.processHEAD(stream, content_type, total_size)
                except:
                    print 'Disconnect from ', stream.getpeername()
                    inputs.remove(stream)
                    stream.close()
                    stream = None


if __name__ == '__main__':
    urls = ["http://103.192.253.24/6971F4187A5308248F216A65CB/0300010C00565DD9C47EDC30059CF77519C53D-C970-A3B0-3E79-3E713E57EA3D.flv.ts",
            "http://101.226.184.77/6972329BBED3E8377C9087529A/0300010C01565DD9C47EDC30059CF77519C53D-C970-A3B0-3E79-3E713E57EA3D.flv.ts",
            "http://220.189.221.181/6972711EB2E4183100805331A7/0300010C02565DD9C47EDC30059CF77519C53D-C970-A3B0-3E79-3E713E57EA3D.flv.ts",
            "http://202.102.93.179/6972AFA1AB63681676E9DB30FE/0300010C03565DD9C47EDC30059CF77519C53D-C970-A3B0-3E79-3E713E57EA3D.flv.ts",
            "http://61.160.205.15/6772711E750408291565783B82/0300010C04565DD9C47EDC30059CF77519C53D-C970-A3B0-3E79-3E713E57EA3D.flv.ts",
            "http://222.73.61.176/6772AFA1DE04281427E1105AF4/0300010C05565DD9C47EDC30059CF77519C53D-C970-A3B0-3E79-3E713E57EA3D.flv.ts",
            "http://101.226.184.25/6572711E4F54783FAC43B3295D/0300010C06565DD9C47EDC30059CF77519C53D-C970-A3B0-3E79-3E713E57EA3D.flv.ts",
            "http://202.102.74.49/6572AFA16F94E8209D3BB02FB0/0300010C07565DD9C47EDC30059CF77519C53D-C970-A3B0-3E79-3E713E57EA3D.flv.ts",
            "http://61.160.198.171/6572EE24EAF4982EF2158E6968/0300010C08565DD9C47EDC30059CF77519C53D-C970-A3B0-3E79-3E713E57EA3D.flv.ts",
            "http://101.226.184.53/6773A9ADB814383C08D9563EF0/0300010C09565DD9C47EDC30059CF77519C53D-C970-A3B0-3E79-3E713E57EA3D.flv.ts",
            "http://202.102.93.171/6773E830B184281B8CFFCB5638/0300010C0A565DD9C47EDC30059CF77519C53D-C970-A3B0-3E79-3E713E57EA3D.flv.ts",
            "http://59.63.171.16/677426B371E377EB9BD786CD0/0300010C0B565DD9C47EDC30059CF77519C53D-C970-A3B0-3E79-3E713E57EA3D.flv.ts"
            ]
    ss = StreamServer()
    print(ss.start(urls))
    #print(ss.getSizes(urls))
