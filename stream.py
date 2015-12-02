# -*- coding: utf-8 -*-

import socket, select, threading, urllib2

BIND_ADDRESS = '0.0.0.0'
STREAM_ADDRESS = '127.0.0.1'
TIMEOUT = 30
MSS = 1440
UA = 'Kodi'

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
        try:
            response = urllib2.urlopen(request)
            info.append(response.info())
        except:
            pass


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
        threading.Thread(target = self.run, args = [server, urls, sizes, content_type]).start()
        return 'http://%s:%d' % (STREAM_ADDRESS, port)

    def sendHead(self, stream, content_type, content_length):
        #Send response to HEAD request
        stream.send('HTTP/1.1 200 OK\r\n'
                    'Content-Type: %s\r\n'
                    'Accept-Ranges: bytes\r\n'
                    'Content-Length: %d\r\n'
                    'Connection: close\r\n\r\n' % (content_type, content_length))

    def processGET(self, stream, header, urls, sizes, content_type, content_length):
        start = 0
        for line in header.split('\r\n'):
            if line[:5].upper() == 'RANGE':
                start = int(line.replace(' ', '').split('=')[1].split('-')[0])
                print 'Starting bytes %d' % (start)
                break

        #Looking for staring url 
        index = 0
        while start >= sizes[index]:
            start -= sizes[index]
            index += 1

        #Get host and path
        port = 80
        host = urls[index].split('/')[2]
        path = '/' + '/'.join(urls[index].split('/')[3:])
        if ':' in host:
            host, port = host.split(':')
            port = int(port)

        #Connect to remote
        agent = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        agent.bind(('', 0))
        agent.settimeout(TIMEOUT)
        agent.connect((host, port))

        #Send GET request
        agent.send('GET %s HTTP/1.1\r\n'
                   'Range: bytes=%d-\r\n'
                   'Host: %s\r\n'
                   'User-Agent: %s\r\n'
                   'Accept: */*\r\n\r\n' % (path, start, host, UA))

        #Receive data from server
        data = agent.recv(MSS)
        if data[9:11] != '20':
            print 'Error status %s' % (data[9:12])
            agent.close()
            return None, 0

        #Send Response to client
        self.sendHead(stream, content_type, content_length)
        skip = data.index('\r\n\r\n') + 4
        stream.send(data[skip:])

        while True:
            data = agent.recv(MSS)
            stream.send(data)

        return stream, index



    def run(self, server, urls, sizes, content_type):
        #Calculate the total size
        total_size = 0
        for size in  sizes:
            total_size += size

        stream = None
        agent = None
        index = 0
        inputs = [server]

        def clean_input(s):
            if s is None:
                return
            if s in inputs:
                inputs.remove(s)
            s.close()
            s = None

        while True:
            readable, _, _ = select.select(inputs, [], [], TIMEOUT)

            #Check timeouts
            if not readable and len(inputs) == 1:
                server.close()
                return

            if server in  readable:
                #New connection from client. Close previous connection. 
                clean_input(stream)
                clean_input(agent)
                stream, _ = server.accept()
                inputs.append(stream)

            if stream in readable:
                #Data from client
                try:
                    data = stream.recv(MSS)
                    if not data:
                        raise
                    print 'Receive data from client:\n%s' % (data)
                    if data[:4].upper() == 'HEAD':
                        self.sendHead(stream, content_type, total_size)
                        raise
                    elif data[:3].upper() == 'GET':
                        clean_input(agent)
                        agent, index = self.processGET(stream, data, urls, sizes, content_type, total_size)
                        if agent is None:
                            raise
                        inputs.append(agent)
                except Exception, e:
                    print(e)
                    clean_input(stream)


if __name__ == '__main__':
    urls = [line.rstrip('\n') for line in open('urls.txt')]
    ss = StreamServer()
    url = ss.start(urls)
    print(url)
    #print(ss.getSizes(urls))

    port = 80
    host = url.split('/')[2]
    path = '/' + '/'.join(url.split('/')[3:])
    if ':' in host:
        host, port = host.split(':')
        port = int(port)

    c = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    c.bind(('', 0))
    c.connect((host, port))
    c.send('GET / HTTP/1.1\r\n'
           'Range: bytes=0-\r\n')
    c.close()
