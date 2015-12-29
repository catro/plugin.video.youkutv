#!/usr/bin/env python
# -*- coding: utf-8 -*-

import socket, select, threading, urllib2, time, struct

class flv:
    @staticmethod
    def modify_duration(data, duration):
        i = data.find('duration')
        if i == -1 or i + 17 > len(data):
            return False, data
        else:
            return True, data[:i + 9] + struct.pack('>d', duration) + data[i + 17:]


    @staticmethod
    def skip_meta(data):
        offset = data.find('FLV')
        if offset == -1:
            return False, data

        offset += 13
        while offset + 15 < len(data):
            t, s1, s2, s3 = struct.unpack('BBBB', data[offset: offset + 4])
            size = (s1 << 16) | (s2 << 8) | s3
            
            if offset + 15 + size > len(data):
                return False, data

            if t != 0x12:
                return True, data[offset:]

            offset += 15 + size

        return False, data

    @staticmethod
    def find_info(data):
        i = data.find('duration')
        if i == -1 or i + 17 > len(data):
            return False, 0, 0
        else:
            duration = struct.unpack('>d', data[i + 9: i + 17])[0]

        start = data.find('FLV')
        offset = start
        if offset == -1:
            return False, 0, 0

        offset += 13
        while offset + 15 < len(data):
            t, s1, s2, s3 = struct.unpack('BBBB', data[offset: offset + 4])
            size = (s1 << 16) | (s2 << 8) | s3
            
            if offset + 15 + size > len(data):
                return False, 0, 0

            if t != 0x12:
                return True, duration, offset - start

            offset += 15 + size

        return False, 0, 0

    @staticmethod
    def modify_timestamp(data, starting_timestamp):
        offset = 0
        ready_data = ''

        while offset + 11 < len(data):
            _, s1, s2, s3, t1, t2, t3, t4 = struct.unpack('BBBBBBBB', data[offset: offset + 8])
            size = (s1 << 16) | (s2 << 8) | s3
            
            if offset + 15 + size > len(data):
                return ready_data

            original_timestamp = (t4 << 24) | (t1 << 16) | (t2 << 8) | t3
            modified_timestamp = original_timestamp + starting_timestamp

            s4 = (modified_timestamp >> 24) & 0xFF
            s1 = (modified_timestamp >> 16) & 0xFF
            s2 = (modified_timestamp >> 8) & 0xFF
            s3 = modified_timestamp & 0xFF

            ready_data += data[offset: offset + 4] 
            ready_data += struct.pack('BBBB', s1, s2, s3, s4)
            ready_data += data[offset + 8: offset + 15 + size]

            offset += 15 + size

        return ready_data

class video_concatenate:
    def __init__(self, 
                 bind_address = ('0.0.0.0', 0),
                 user_agent = 'video_concatenate',
                 timeout = 10,
                 mss = 1460,
                 debug = True,
                ):


        self.server = None
        self.agent_server = None
        self.agent_client = None

        self.total_size = 0
        self.total_seconds = 0
        self.videos = []

        self.config = {'la': bind_address,
                       'ua': user_agent,
                       'timeout': timeout,
                       'mss': mss,
                       'debug': debug,
                      }

        self.thread = threading.Thread(target = self._run)
        self.running = False



    def _cleanup(self):
        if self.server:
            self.log('server closed.')
            s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
            s.bind(('', 0))
            try:
                s.connect(self.server.getsockname())
            except:
                pass
            if self.thread and self.thread.isAlive():
                self.thread.join()
            s.close()
            self.server.close()
            self.server = None
        if self.agent_server:
            self.agent_server.close()
            self.agent_server = None
        if self.agent_client:
            self.agent_client.close()
            self.agent_client = None


    def __del__(self):
        self.log('Service deleted')
        self.stop()


    def _get_info(self, urls):
        infos = []
        threads = []

        def __get_info(url, info):
            timeout = self.config['timeout']
            s = self._connect_to_url(url)
            data = ''
            inputs = []
            outputs = [s]
            length = 0
            t = ''

            while True:
                readable, writable, _ = select.select(inputs, outputs, [], timeout)
                if len(readable) == 0 and len(writable) == 0:
                    self.log('get info error due to timeout')
                    break
                if s.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR):
                    self.log('get info error due to socket error')
                    break

                if len(writable) == 1:
                    self._send_get(s, 0, url)
                    inputs = [s]
                    outputs = []

                if len(readable) == 1:
                    try:
                        tmp = s.recv(self.config['mss'])
                    except:
                        tmp = ''

                    if len(tmp) == 0:
                        break

                    data += tmp
                    if length == 0 or t == '':
                        if data.find('\r\n\r\n') == -1:
                            continue
                        i = data.upper().find('CONTENT-LENGTH')
                        if i == -1:
                            break
                        length = int(data[i:].split('\r\n')[0].replace(' ', '').split(':')[1])

                        i = data.upper().find('CONTENT-TYPE')
                        if i == -1:
                            break
                        t = data[i:].split('\r\n')[0].replace(' ', '').split(':')[1]

                    ret, duration, offset = flv.find_info(data)
                    if ret == False:
                        continue

                    info.append({'url': url,
                                 'size': length,
                                 'content-type': t,
                                 'duration': duration,
                                 'offset': offset})
                    break

            s.close()
            return

        #Get info concurrently. 
        for url in  urls:
            infos.append([])
            t = threading.Thread(target = __get_info, args = [url, infos[-1]])
            t.start()
            threads.append(t)

        for t in threads:
            t.join()

        if len(infos) == 0:
            return [], ''

        videos = []
        for i in range(len(infos)):
            if len(infos[i]) == 0:
                return []
            videos.append(infos[i][0])

        return videos


    def _send_head(self, starting_bytes, content_type):
        #Send response to HEAD request
        self.agent_server.send('HTTP/1.1 200 OK\r\n'
                               'Content-Type: %s\r\n'
                               'Accept-Ranges: bytes\r\n'
                               'Content-Length: %d\r\n'
                               'Connection: close\r\n\r\n' % (content_type, 
                                                              self.total_size - starting_bytes))


    def _send_get(self, s, starting_bytes, url):
        self.log('send GET request(%d) to %s' % (starting_bytes, url))

        #Calculate the host and path
        host = url.split('/')[2]
        path = '/' + '/'.join(url.split('/')[3:])

        #Send GET request
        s.send('GET %s HTTP/1.1\r\n'
               'Range: bytes=%d-\r\n'
               'Host: %s\r\n'
               'User-Agent: %s\r\n'
               'Accept: */*\r\n\r\n' % (path, starting_bytes, host, self.config['ua']))


    def _find_starting(self, data):
        start = 0
        for line in data.split('\r\n'):
            if line[:5].upper() == 'RANGE':
                start = int(line.replace(' ', '').split('=')[1].split('-')[0])
                break

        relative = start
        index = 0
        for i in range(len(self.videos)):
            if relative < self.videos[i]['size']:
                break
            else:
                relative -= self.videos[i]['size'] 
                index += 1

        self.log('starting bytes: %d' % (start))
        self.log('relative starting bytes: %d' % (relative))

        return start, relative, index


    def _connect_to_url(self, url):
        #Get host and path
        port = 80
        host = url.split('/')[2]
        if ':' in host:
            host, port = host.split(':')
            port = int(port)

        #Connect to remote
        s = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        s.bind(('', 0))
        s.setblocking(False)
        try:
            s.connect((host, port))
        except:
            pass
        return s


    def _run(self):
        self.log('running')
        inputs = [self.server]
        outputs = []
        readable = []
        writable = []
        recv_buffer = ''
        send_buffer = ''
        header = ''
        starting_bytes = 0
        index = 0
        skip_header = True
        skip_meta = True
        modify_timestamp = True
        modify_duration = True

        def _clean_socket(s):
            if s is None:
                return
            for arr in [inputs, outputs, readable, writable]:
                if s in arr:
                    arr.remove(s)
            s.close()

        while True: 
            while None in inputs:
                inputs.remove(None)
            while None in outputs:
                outputs.remove(None)
                
            if len(inputs) == 0:
                self.log('no inputs')
                break

            try:
                readable, writable, _ = select.select(inputs, outputs, [], self.config['timeout'])
            except:
                self.log('select error')
                break

            if self.running == False:
                self.log('Stopped')
                break

            if not readable and not writable and len(inputs) == 1 and len(outputs) == 0:
                #Timeouts
                self.log('select timeout')
                break

            #Loop to process all sockets in readable array
            for s in readable:
                if s == self.server:
                    self.log('new connection')
                    #Accept new connection
                    _clean_socket(self.agent_server)
                    _clean_socket(self.agent_client)
                    self.agent_server = self.server.accept()[0]
                    self.agent_server.setblocking(False)
                    self.agent_client = None
                    inputs.append(self.agent_server)
                    recv_buffer = ''
                    send_buffer = ''
                    header = ''
                    starting_bytes = 0
                    relative_starting_bytes = 0
                    index = 0
                    continue

                err = s.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR)
                if err:
                    if s == self.agent_client:
                        self.log('agent client error: %d' % (err))
                    else:
                        self.log('agent server error: %d' % (err))
                    #Process socket error
                    _clean_socket(self.agent_server)
                    _clean_socket(self.agent_client)
                    self.agent_server = None
                    self.agent_client = None
                    continue

                if s == self.agent_client:
                    #Receive data from remote
                    try:
                        tmp = self.agent_client.recv(self.config['mss'])
                    except:
                        tmp = None

                    if not tmp:
                        #No more data from remote
                        _clean_socket(self.agent_client)
                        self.agent_client = None
                        if index + 1 < len(self.videos):
                            index += 1
                            self.log('switch to vedio %d' % (index))
                            self.log('starting timestamp: %f' % (self.videos[index]['starting_ms']))
                            url = self.videos[index]['url']
                            self.agent_client = self._connect_to_url(url)
                            outputs.append(self.agent_client)
                            relative_starting_bytes = 0
                            modify_duration = False
                            skip_meta = True
                            modify_timestamp = True
                            skip_header = True
                        continue

                    recv_buffer += tmp

                    ready = True

                    #Skip header
                    if skip_header == True:
                        i = recv_buffer.find('\r\n\r\n')
                        if i == -1:
                            self.log('header not complete')
                            ready = False
                        else:
                            self.log('header skipped')
                            recv_buffer = recv_buffer[i + 4:]
                            skip_header = False

                    #Modify duration
                    if ready == True and modify_duration == True:
                        ready, recv_buffer = flv.modify_duration(recv_buffer, self.total_seconds)
                        if ready:
                            self.log('duration modified')
                            modify_duration = False
                        else:
                            self.log('duration not found')

                    #Skip meta data
                    if ready == True and skip_meta == True:
                        ready, recv_buffer = flv.skip_meta(recv_buffer)
                        if ready:
                            self.log('meta skipped')
                            skip_meta = False
                        else:
                            self.log('meta not complete')

                    if ready == True and modify_timestamp == True:
                        ready_data = flv.modify_timestamp(recv_buffer, self.videos[index]['starting_ms'])
                    else:
                        ready_data = recv_buffer

                    #Check receive buffer
                    if len(ready_data) == 0:
                        ready = False

                    if ready == False:
                        continue

                    #Receive buffer is ready
                    send_buffer += ready_data
                    recv_buffer = recv_buffer[len(ready_data):]

                    if self.agent_server not in outputs:
                        outputs.append(self.agent_server)

                    continue

                if s == self.agent_server:
                    try:
                        tmp = self.agent_server.recv(self.config['mss'])
                    except:
                        tmp = None
                    
                    if not tmp:
                        #Local closed the socket
                        _clean_socket(self.agent_server)
                        _clean_socket(self.agent_client)
                        self.agent_server = None
                        self.agent_client = None
                        continue

                    #Append to header
                    header += tmp

                    if header.find('\r\n\r\n') == -1:
                        #Header not complete
                        continue

                    starting_bytes, relative_starting_bytes, index = self._find_starting(header)
                    self.log('starting timestamp: %f' % (self.videos[index]['starting_ms']))

                    if starting_bytes < self.total_size:
                        if header[:3].upper() == 'GET':
                            self.log('receive GET request')
                            url = self.videos[index]['url']
                            _clean_socket(self.agent_client)
                            self.agent_client = self._connect_to_url(url)
                            outputs.append(self.agent_client)

                            if starting_bytes == 0:
                                modify_duration = True
                                skip_meta = False
                                modify_timestamp = False
                            elif relative_starting_bytes == 0:
                                modify_duration = False
                                skip_meta = True
                                modify_timestamp = True
                            skip_header = True
                            self._send_head(starting_bytes, self.videos[index]['content-type'])
                            header = ''
                            continue

                        if header[:4].upper() == 'HEAD':
                            self.log('receive HEAD request')
                            self._send_head(starting_bytes, self.videos[index]['content-type'])

                    header = ''
                    _clean_socket(self.agent_server)
                    self.agent_server = None

                    continue

                if s in inputs:
                    inputs.remove(s)

            #Loop to process all sockets in readable array
            for s in writable:
                if s.getsockopt(socket.SOL_SOCKET, socket.SO_ERROR):
                    #Process socket error
                    _clean_socket(self.agent_client)
                    _clean_socket(self.agent_server)
                    self.agent_client = None
                    self.agent_server = None
                    continue

                if s == self.agent_client:
                    #Send GET request
                    self._send_get(self.agent_client, relative_starting_bytes, url)
                    outputs.remove(self.agent_client)
                    if self.agent_client not in inputs:
                        inputs.append(self.agent_client)
                    continue

                if s == self.agent_server:
                    #Send data to local socket
                    sent = self.agent_server.send(send_buffer)

                    if sent == len(send_buffer):
                        #All data sent
                        outputs.remove(self.agent_server)

                        if self.agent_client == None:
                            _clean_socket(self.agent_server)
                            self.agent_server = None
                        elif self.agent_client not in inputs:
                            inputs.append(self.agent_client)
                        send_buffer = ''

                    else:
                        #Partial data sent
                        send_buffer = send_buffer[sent:]
                        if self.agent_client in inputs:
                            inputs.remove(self.agent_client)

                    continue

                if s in inputs:
                    inputs.remove(s)


        if self.running == True:
            #Cleanup
            self.server.close()
            self.server = None
            self._cleanup()

        self.log('thread exit')


    #APIs
    def log(self, s):
        if self.config['debug'] == 1:
            print('[%s][video_concatenate]%s' % (time.time(), s))


    #Start agent thread
    def start(self, urls):
        self.stop()
        self.running = True

        #Create server socket
        self.server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
        self.server.bind(self.config['la'])
        self.server.listen(5)
        self.server.setblocking(False)

        address, port = self.server.getsockname()
        self.log('server listen at %s:%d' % (address, port))

        #Get size and content type
        videos = self._get_info(urls)

        if len(videos) == 0 or len(videos) != len(urls):
            self.log('Failed to process urls.')
            raise

        #Construct videos
        total_size = 0
        total_seconds = 0
        for i in range(len(videos)):
            if i != 0:
                videos[i]['size'] -= videos[i]['offset']
            videos[i]['starting_bytes'] = total_size
            videos[i]['starting_ms'] = int(total_seconds * 1000)
            total_size += videos[i]['size']
            total_seconds += videos[i]['duration']
            self.log(videos[i])

        #Set video variables
        self.total_size = total_size 
        self.total_seconds = total_seconds
        self.videos = videos

        #Start thread.
        self.thread = threading.Thread(target = self._run)
        self.thread.start()


    def stop(self):
        self.running = False
        self._cleanup()
        self.thread = None


    def get_port(self):
        try:
            return self.server.getsockname()[1]
        except:
            return 0


if __name__ == '__main__':
    urls = [line.rstrip('\n') for line in open('urls.txt')]
    vc = video_concatenate(('0.0.0.0', 7777))
    vc.start(urls)
    #vc.stop()

    #vc.add_agent(urls)
    #vc.delete_agent(url)
    #vc.delete_agent(url)
    #vc.add_agent(urls)
    #ss = StreamServer()
    #url = ss.start(urls)
    #print(url)
    ##print(ss.getSizes(urls))

    #port = 80
    #host = url.split('/')[2]
    #path = '/' + '/'.join(url.split('/')[3:])
    #if ':' in host:
    #    host, port = host.split(':')
    #    port = int(port)

    #c = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
    #c.bind(('', 0))
    #c.connect((host, port))
    #c.send('GET / HTTP/1.1\r\n'
    #       'Range: bytes=0-\r\n')
    #c.close()
