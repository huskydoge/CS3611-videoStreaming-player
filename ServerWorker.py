from random import randint
import sys, traceback, threading, socket

from VideoStream import VideoStream
from RtpPacket import RtpPacket


# These two modules implement the server which responds to the RTSP requests and streams back the video. The RTSP interaction is already implemented and the ServerWorker calls methods from the RtpPacket class to packetize the video data.

# You do not need to modify these modules.

class ServerWorker:
    SETUP = 'SETUP'
    PLAY = 'PLAY'
    PAUSE = 'PAUSE'
    TEARDOWN = 'TEARDOWN'
    DESCRIBE = 'DESCRIBE'
    FWD = "FORWARD"
    REV = "REVERSE"

    INIT = 0
    READY = 1
    PLAYING = 2
    state = INIT

    OK_200 = 0
    FILE_NOT_FOUND_404 = 1
    CON_ERR_500 = 2

    clientInfo = {}

    # kinds of streams in the session and what encodings are used.
    stream_type = 'video'
    MJPEG_TYPE = 'video/x-mjpeg'

    def __init__(self, clientInfo):
        self.clientInfo = clientInfo

    def run(self):
        threading.Thread(target=self.recvRtspRequest).start()

    def recvRtspRequest(self):
        """Receive RTSP request from the client."""
        connSocket = self.clientInfo['rtspSocket'][0]
        while True:
            data = connSocket.recv(256)  # Receive data from the client
            if data:
                print("Data received:\n" + data.decode("utf-8"))
                self.processRtspRequest(data.decode("utf-8"))

    def processRtspRequest(self, data):
        """Process RTSP request sent from the client."""
        # Get the request type
        request = data.split('\n')
        line1 = request[0].split(' ')
        requestType = line1[0]

        # Get the media file name
        filename = line1[1]

        # Get the RTSP sequence number
        seq = request[1].split(' ')

        # Process SETUP request
        if requestType == self.SETUP:
            if self.state == self.INIT:

                print("Sending Total number of Frames")

                # Update state
                print("processing SETUP\n")

                try:
                    self.clientInfo['videoStream'] = VideoStream(filename)
                    self.state = self.READY
                except IOError:
                    self.replyRtsp(self.FILE_NOT_FOUND_404, seq[1])
                total_frames_num = self.clientInfo['videoStream'].get_total_frames_num()
                # print("toatl in worker",total_frames_num)
                # Generate a randomized RTSP session ID
                self.clientInfo['session'] = randint(100000, 999999)

                # Send RTSP reply
                self.SendTotalFrame(total_frames_num, seq[1])
                # self.replyRtsp(self.OK_200, seq[1])

                # Get the RTP/UDP port from the last line
                self.clientInfo['rtpPort'] = request[2].split(' ')[2]

        # Process PLAY request
        elif requestType == self.PLAY:
            # send the sum of frames

            if self.state == self.READY:
                print("processing PLAY\n")
                self.state = self.PLAYING

                # Create a new socket for RTP/UDP
                self.clientInfo["rtpSocket"] = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

                self.replyRtsp(self.OK_200, seq[1])

                # Create a new thread and start sending RTP packets
                self.clientInfo['event'] = threading.Event()
                self.clientInfo['worker'] = threading.Thread(target=self.sendRtp)
                self.clientInfo['worker'].start()



        # Process PAUSE request
        elif requestType == self.PAUSE:
            if self.state == self.PLAYING:
                print("processing PAUSE\n")
                self.state = self.READY

                self.clientInfo['event'].set()

                '''self.clientInfo['event'].set()用于设置一个threading.Event对象的内部标志。
                threading.Event是Python标准库中提供的一个线程同步原语，它可以在多个线程之间进行通信和协调。
                Event对象被用作一个信号，以控制媒体流发送线程的暂停（PAUSE）和继续。
                当处理到客户端发来的PAUSE请求时，会调用self.clientInfo['event'].set()来设置Event对象的内部标志。
                这将导致在sendRtp方法中使用self.clientInfo['event'].wait()来阻塞的工作线程停止等待，并暂停发送媒体流数据。
                当其他操作（如PLAY请求）需要重新开始发送媒体流时，可以通过调用self.clientInfo['event'].clear()来清除Event对象的内部标志。
                '''

                self.replyRtsp(self.OK_200, seq[1])

        # Process TEARDOWN request
        elif requestType == self.TEARDOWN:
            print("processing TEARDOWN\n")

            # Join the worker thread to ensure it has terminated before continuing
            self.clientInfo['worker'].join()
            self.clientInfo['event'].set()

            self.replyRtsp(self.OK_200, seq[1])

            # Close the RTP socket
            self.clientInfo['rtpSocket'].close()

        # Process DESCRIBE request
        elif requestType == self.DESCRIBE:
            print("processing DESCRIBE\n")

            sdpDescription = "v=0\r\n" \
                             "o=- 0 0 IN IP4 {serverAddress}\r\n" \
                             "s={streamName}\r\n" \
                             "c=IN IP4 {clientAddress}\r\n" \
                             "m=video {clientRtpPort} RTP/AVP 26\r\n" \
                             "a=rtpmap:26 {mjpegType}/90000\r\n"

            # Replace placeholders with actual values
            serverAddress = self.clientInfo['rtspSocket'][1][0]
            clientAddress = self.clientInfo['rtspSocket'][0].getpeername()[0]
            streamName = self.clientInfo['videoStream'].get_filename()
            clientRtpPort = self.clientInfo['rtpPort']
            mjpegType = self.MJPEG_TYPE

            sdpDescription = sdpDescription.format(serverAddress=serverAddress, streamName=streamName,
                                                   clientAddress=clientAddress, clientRtpPort=clientRtpPort,
                                                   mjpegType=mjpegType)

            # Send the DESCRIBE response with the SDP description
            print("Sending DESCRIBE response:\n" + sdpDescription)
            self.replyDescribe(sdpDescription, seq[1])
        elif requestType == self.FWD:
            print("processing FORWARD\n")
            self.clientInfo['videoStream'].movepoint(100)
            # self.state = self.READY

        elif requestType == self.REV:

            print("processing REVERSE\n")
            self.clientInfo['videoStream'].revpoint(100)

    def sendRtp(self):
        """Send RTP packets over UDP."""
        while True:
            self.clientInfo['event'].wait(0.05)

            # Stop sending if request is PAUSE or TEARDOWN
            if self.clientInfo['event'].isSet():
                break

            data = self.clientInfo['videoStream'].nextFrame()  # 每次发送一帧
            if data:
                frameNumber = self.clientInfo['videoStream'].frameNbr()
                try:
                    address = self.clientInfo['rtspSocket'][1][0]
                    port = int(self.clientInfo['rtpPort'])
                    self.clientInfo['rtpSocket'].sendto(self.makeRtp(data, frameNumber),
                                                        (address, port))  # 需要用RTP格式进行封装
                except:
                    print("Connection Error")
                # print('-'*60)
                # traceback.print_exc(file=sys.stdout)
                # print('-'*60)

    def makeRtp(self, payload, frameNbr):
        """RTP-packetize the video data."""
        version = 2
        padding = 0
        extension = 0
        cc = 0
        marker = 0
        pt = 26  # MJPEG type
        seqnum = frameNbr
        ssrc = 0

        rtpPacket = RtpPacket()

        rtpPacket.encode(version, padding, extension, cc, seqnum, marker, pt, ssrc, payload)

        return rtpPacket.getPacket()

    # 用于发送RTSP响应，针对DESCRIBE请求
    def replyDescribe(self, sdpDescription, cseq):
        # Send the RTSP response with the SDP description for the DESCRIBE request
        reply = 'RTSP/1.0 200 OK\nCSeq: {}\n'.format(cseq) + \
                'Session: ' + str(self.clientInfo['session']) + '\n' + \
                'Content-Type: application/sdp\r\nContent-Length: {}\r\n\r\n{}'.format(len(sdpDescription),
                                                                                       sdpDescription)
        print(reply)
        self.clientInfo['rtspSocket'][0].send(reply.encode())

    # 用于发送总的帧数
    def SendTotalFrame(self, total_frames_num, cseq):
        reply = 'RTSP/1.0 200 OK\nCSeq: {}\n'.format(cseq) + \
                'Session: ' + str(self.clientInfo['session']) + '\n' + \
                'Total: {}'.format(total_frames_num)

        print(reply)
        self.clientInfo['rtspSocket'][0].send(reply.encode())

    def replyRtsp(self, code, seq):
        """Send RTSP reply to the client."""
        if code == self.OK_200:
            print("200 OK")
            reply = 'RTSP/1.0 200 OK\nCSeq: ' + seq + '\nSession: ' + str(self.clientInfo['session'])
            connSocket = self.clientInfo['rtspSocket'][0]
            connSocket.send(reply.encode())

        # Error messages
        elif code == self.FILE_NOT_FOUND_404:
            print("404 NOT FOUND")
        elif code == self.CON_ERR_500:
            print("500 CONNECTION ERROR")
