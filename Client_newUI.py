from tkinter import *
from tkinter.messagebox import *
from tkinter import messagebox
from PIL import Image, ImageTk
import socket, threading, sys, traceback, os, time
import ttkbootstrap as ttk
import pickle
from ttkbootstrap.icons import Emoji

from ttkbootstrap.constants import *

from RtpPacket import RtpPacket

CACHE_FILE_NAME = "cache-"
CACHE_FILE_EXT = ".jpg"

bits_per_second_list = []
total_bytes_list = []
packages_loss_rate_list = []
packages_loss_list = []


# # In the Client class, you will need to implement the actions that are taken when the buttons are pressed. You do not need to modify the ClientLauncher module.

class Client(ttk.Frame):
    INIT = 0
    READY = 1
    PLAYING = 2
    state = INIT

    SETUP = 0
    PLAY = 1
    PAUSE = 2
    TEARDOWN = 3
    DESCRIBE = 4
    FWD = 5
    REV = 6

    # Initiation..
    def __init__(self, master, serveraddr, serverport, rtpport, filename):
        super().__init__(master)
        self.rev = False
        self.record_rev_frame = 0
        self.background = None  # for media window, initial background
        self.server_addr_entry = None
        # self.master.resizable(False, False)
        self.photo = None  # for media window
        self.menu = None  # menu bar
        self.request_dict = {-1: 'NONE', 0: 'SETUP', 1: 'PLAY', 2: 'PAUSE', 3: 'TEARDOWN',
                             4: 'DESCRIBE', 5: 'FORWARD', 6: 'REVERSE'}  # request type

        # button groups
        self.teardown = None
        self.pause = None
        self.start = None
        self.describe = None
        self.info = None

        self.master = master
        self.master.protocol("WM_DELETE_WINDOW", self.handler)

        # self.createWidgets() # GUI
        self.serverAddr = serveraddr
        self.serverPort = int(serverport)
        self.rtpPort = int(rtpport)
        self.fileName = filename
        self.rtspSeq = 0
        self.sessionId = 0
        self.requestSent = -1
        self.teardownAcked = 0
        self.connectToServer()
        self.frameNbr = 0
        self.time = time.time()
        self.totalBytes = 0
        self.bits_per_second = 0
        self.first_play = True

        # added by hbh, packet loss rate, 5.21
        self.packages_loss = 0
        self.packages_loss_rate = 0
        self.state_dict = {0: "INIT", 1: "READY", 2: "PLAYING"}
        self.encodingFormat = ''
        self.payloadType = ''
        self.sessionType = ''  # session type, audio or video，etc
        self.total_frames = 0
        self.total_frames_updated = False
        self.frame_offset = 0

        ## GUI

        self.pack(fill=BOTH, expand=YES)  # fill parent window
        self.hdr_var = ttk.StringVar()  # header message

        self.elapsed_var = ttk.DoubleVar(value=0)  # progress meter
        self.remain_var = ttk.DoubleVar(value=self.total_frames)  # progress meter
        self.create_Widgets()
        self.colors = [
            "#FF5733",  # 橙色
            "#C70039",  # 红色
            "#900C3F",  # 深红
            "#581845",  # 紫色
            "#39FF14",  # 绿色
            "#00FFFF",  # 青色
            "#0000FF",  # 蓝色
            "#8A2BE2"  # 矿蓝
        ]

    def create_menu(self):
        """Create menu bar"""
        self.menu = ttk.Menu(self.master)

        # 创建一个 "File" 菜单并添加到菜单栏
        infomenu = ttk.Menu(self.menu, tearoff=0)
        infomenu.add_command(label="RTSP Info", command=self.ShowInfo)
        infomenu.add_command(label="Describe", command=self.ShowDescribe)
        infomenu.add_command(label="Setup", command=self.setupMovie)
        self.menu.add_cascade(label="More Info", menu=infomenu)
        self.menu.add_command(label="Set Client", command=self.open_set_client)

        # # 创建一个 "Tool" 菜单并添加到菜单栏
        toolmenu = ttk.Menu(self.master, tearoff=0)
        toolmenu.add_command(label="fast forward", command=self.playfwd)
        toolmenu.add_command(label="roll back", command=self.playrev)
        toolmenu.add_command(label="pause", command=self.pauseMovie)
        toolmenu.add_command(label="play", command=self.playMovie)
        self.menu.add_cascade(label="Tool Box", menu=toolmenu)

        client_menu = ttk.Menu(self.menu)
        client_menu.add_command(label="Set Client", command=self.open_set_client)
        client_menu.add_command(label="About", command=self.about)
        client_menu.add_command(label="Exit", command=self.exitEXE)
        self.menu.add_cascade(label="Client Menu", menu=client_menu)
        self.master.config(menu=self.menu)

    def create_header(self):
        """The application header to display user messages"""
        self.hdr_var.set("The demo of Video Streaming Player based on RTSP/RTP")
        lbl = ttk.Label(
            master=self,
            textvariable=self.hdr_var,
            bootstyle=(LIGHT, INVERSE),
            padding=10
        )
        lbl.pack(fill=X, expand=YES)

        # 添加一个Frame控件
        # frame = ttk.Frame(self)
        # frame.pack(pady=5)
        #
        # self.filename_var = StringVar()
        #
        # # 将Entry和Button添加到Frame中
        # entry = ttk.Entry(frame, textvariable=self.filename_var)
        # button = ttk.Button(frame, text="load file", command=self.change_filename_and_play)
        # entry.pack(side=LEFT, fill=X, padx=(0, 10), ipadx=0)  # 将ipadx设为0，实现左对齐
        # button.pack(side=LEFT)

    def change_filename_and_play(self):
        self.fileName = self.filename_var.get()
        self.setupMovie()

    def create_media_window(self):
        """Create frame to contain media"""
        img_path = "background.jpg"
        self.background = ImageTk.PhotoImage(file=img_path)
        self.media = Label(self, image=self.background, width=500, height=600)
        # self.media = ttk.Label(self, width=50)
        self.media.pack(anchor="center", fill="both", expand=True)

    def create_progress_meter(self):
        """Create frame with progress meter with lables"""
        container = ttk.Frame(self)
        container.pack(fill=X, expand=YES, pady=10)

        self.elapse = ttk.Label(container, text='Fr: {}'.format(int(self.elapsed_var.get())))
        self.elapse.pack(side=LEFT, padx=10)

        self.scale = ttk.Scale(
            master=container,
            command=self.on_progress,
            bootstyle=SECONDARY
        )
        self.scale.pack(side=LEFT, fill=X, expand=YES)

        self.remain = ttk.Label(container, text='Fr: {}'.format(int(self.remain_var.get())))
        self.remain.pack(side=LEFT, fill=X, padx=10)

    def create_buttonbox(self):
        """Create buttonbox with media controls"""
        container = ttk.Frame(self)  # create a frame
        container.pack(fill=X, expand=YES)  # pack the frame
        ttk.Style().configure('TButton', font="-size 14")  # configure style

        # 回退
        rev_btn = ttk.Button(
            master=container,
            text=Emoji.get('black left-pointing double triangle with vertical bar'),
            padding=10,
            command=self.playrev
        )
        rev_btn.pack(side=LEFT, fill=X, expand=YES)

        play_btn = ttk.Button(
            master=container,
            text=Emoji.get('black right-pointing triangle'),
            padding=10,
            command=self.playMovie
        )
        play_btn.pack(side=LEFT, fill=X, expand=YES)

        # 快进
        fwd_btn = ttk.Button(
            master=container,
            text=Emoji.get('black right-pointing double triangle with vertical bar'),
            padding=10,
            command=self.playfwd
        )
        fwd_btn.pack(side=LEFT, fill=X, expand=YES)

        # 暂停
        pause_btn = ttk.Button(
            master=container,
            text=Emoji.get('double vertical bar'),
            padding=10,
            command=self.pauseMovie
        )
        pause_btn.pack(side=LEFT, fill=X, expand=YES)

        stop_btn = ttk.Button(
            master=container,
            text=Emoji.get('black square for stop'),
            padding=10,
            command=self.exitClient
        )
        stop_btn.pack(side=LEFT, fill=X, expand=YES)

        # stop_btn = ttk.Button(
        #     master=container,
        #     text=Emoji.get('open file folder'),
        #     bootstyle=SECONDARY,
        #     padding=10
        # )
        # stop_btn.pack(side=LEFT, fill=X, expand=YES)
        self.stop_btn = stop_btn
        self.pause_btn = pause_btn
        self.play_btn = play_btn
        self.rev_btn = rev_btn

    def fast_forward(self):
        # TODO: fast forward
        pass

    def rollback(self):
        # TODO: rollback
        pass

    def on_progress(self, val: float):
        """Update progress labels when the scale is updated."""
        if self.total_frames_updated is False and self.total_frames > 0:
            print('update!')
            self.remain_var.set(self.total_frames)
            self.total_frames_updated = True

        elapsed = self.elapsed_var.get()
        remaining = self.remain_var.get()
        total = int(elapsed + remaining)

        elapse = int(float(val) * total)
        # elapse_min = elapse // 60
        # elapse_sec = elapse % 60

        remain_tot = total - elapse
        # remain_min = remain_tot // 60
        # remain_sec = remain_tot % 60

        self.elapsed_var.set(elapse)
        self.remain_var.set(remain_tot)
        #
        # self.elapse.configure(text=f'{elapse_min:02d}:{elapse_sec:02d}')
        # self.remain.configure(text=f'{remain_min:02d}:{remain_sec:02d}')

        self.elapse.configure(text=f'Fr: {elapse}')
        self.remain.configure(text=f'Fr: {remain_tot}')

    # create GUI
    def create_Widgets(self):
        self.create_header()  # header message
        self.create_media_window()  # media window
        self.create_progress_meter()  # progress meter
        self.create_buttonbox()  # media controls
        self.create_menu()  # menu bar

    def ShowDescribe(self):
        """Describe button handler."""
        self.sendRtspRequest(self.DESCRIBE)
        """Info button handler."""
        describe = Toplevel()
        # describe.resizable(False, False)
        describe.title('Stream Type in Session and Encoding Format')

        # 创建一个 Frame 作为容器
        container = ttk.Frame(describe, padding=20)
        container.pack(fill="both", expand=True)
        s = StringVar(value="")

        labels = [
            "Session Stream Type",
            "Encoding Format",
            "Payload Type"
        ]

        for i, label_text in enumerate(labels):
            label = ttk.Label(container, text=label_text + ":", font=("Helvetica", 14))
            label.grid(row=i, column=0, sticky="w")  # sticky="w" 左对齐

        def refresh_info():
            """Refresh the info displayed in the window."""
            values = [
                str(self.sessionType),
                str(self.encodingFormat),
                str(self.payloadType)
            ]

            for i, value_text in enumerate(values):
                value_label = ttk.Label(container, text=value_text, font=("Helvetica", 14))
                value_label.grid(row=i, column=1, sticky="w")

            describe.after(1000, refresh_info)

        describe.after(1000, refresh_info)

    '''
    created by hbh, info render
    '''

    def about(self):
        members = "朱鹏翔，李佳鑫，周晟洋，黄奔皓"
        project_link = "https://github.com/huskydoge/CS3601-videoStreaming-player"
        messagebox.showinfo("Group Members and Project Link",
                            f"Group Members:\n{members}\n\nProject Link: {project_link}", icon="info")

    def ShowInfo(self):
        """Info button handler."""
        top = ttk.Toplevel(iconphoto='myicon.ico')
        # top.resizable(False, False)
        top.title('Information about streaming state')
        # 创建一个 Frame 作为容器
        # 创建一个 Frame 作为容器
        container = ttk.Frame(top, padding=20)
        container.pack(fill="both", expand=True)

        labels = [
            "Client state",
            "CSeq",
            "RTP sequence number",
            "Total bytes received",
            "Bits per second",
            "Package loss",
            "Package loss rate",
            "Server address",
            "Server port",
            "rtp port",
            "File name",
            "Session id",
            "Request sent",
            "Teardown acked",
            # "Connect to server",
            "First play"
        ]

        for i, label_text in enumerate(labels):
            # color = random.choice(self.colors)  # 从颜色列表中随机选择颜色
            label = ttk.Label(container, text=label_text + ":", relief="groove", font=("Helvetica", 14))
            label.grid(row=i, column=0, sticky="w", padx=(10, 0), pady=5)  # sticky="w" 左对齐

        def refresh_info():
            """Refresh the info displayed in the window."""
            values = [
                str(self.state) + ": " + self.state_dict[self.state],
                str(self.rtspSeq),
                str(self.frameNbr),
                str(self.totalBytes),
                str(self.bits_per_second),
                str(self.packages_loss),
                str(self.packages_loss_rate * 100) + "%",
                str(self.serverAddr),
                str(self.serverPort),
                str(self.rtpPort),
                str(self.fileName),
                str(self.sessionId),
                str(self.requestSent) + "({})".format(self.request_dict[self.requestSent]),
                str(self.teardownAcked),
                # str(self.connectToServer),
                str(bool(self.first_play))
            ]

            for i, value_text in enumerate(values):
                value_label = ttk.Label(container, text=value_text, font=("Helvetica", 14))
                value_label.grid(row=i, column=1, sticky="w", padx=(5, 10), pady=5)

            top.after(1000, refresh_info)

        top.after(1000, refresh_info)

    def setupMovie(self):
        """Setup button handler."""
        if self.state == self.INIT:
            self.sendRtspRequest(self.SETUP)

    def exitEXE(self):
        """Exit EXE"""
        sys.exit()

    def open_set_client(self):
        set_client_window = Toplevel(self.master)
        set_client_window.title("Set Client")

        ttk.Label(set_client_window, text="Server Address:").grid(row=0, column=0, padx=5, pady=5, sticky=W)
        self.server_addr_entry = ttk.Entry(set_client_window, width=20)
        self.server_addr_entry.insert(0, "127.0.0.1")
        self.server_addr_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(set_client_window, text="Server Port:").grid(row=1, column=0, padx=5, pady=5, sticky=W)
        self.server_port_entry = ttk.Entry(set_client_window, width=20)
        self.server_port_entry.insert(0, "6666")
        self.server_port_entry.grid(row=1, column=1, padx=5, pady=5)

        ttk.Label(set_client_window, text="RTP Port:").grid(row=2, column=0, padx=5, pady=5, sticky=W)
        self.rtp_port_entry = ttk.Entry(set_client_window, width=20)
        self.rtp_port_entry.insert(0, "5008")
        self.rtp_port_entry.grid(row=2, column=1, padx=5, pady=5)

        ttk.Label(set_client_window, text="Filename:").grid(row=3, column=0, padx=5, pady=5, sticky=W)
        self.filename_entry = ttk.Entry(set_client_window, width=20)
        self.filename_entry.insert(0, "movie.Mjpeg")
        self.filename_entry.grid(row=3, column=1, padx=5, pady=5)

        submit_button = ttk.Button(set_client_window, text="Submit", command=self.set_client_params)
        submit_button.grid(row=4, columnspan=2, pady=(5, 10))

    def set_client_params(self):
        self.serverAddr = self.server_addr_entry.get()
        self.serverPort = int(self.server_port_entry.get())
        self.rtpPort = int(self.rtp_port_entry.get())
        self.fileName = self.filename_entry.get()

    def exitClient(self):
        """Teardown button handler."""
        self.sendRtspRequest(self.TEARDOWN)
        self.master.destroy()  # Close the gui window
        os.remove(CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT)  # Delete the cache image from video

        print("get out ")
        sys.exit()

    def pauseMovie(self):
        """Pause button handler."""
        if self.state == self.PLAYING:
            self.sendRtspRequest(self.PAUSE)

    def playrev(self):
        """REV button handler."""
        if self.state == self.PLAYING:
            # send a request for rev
            print("put the rev")
            self.sendRtspRequest(self.REV)

    def playfwd(self):
        """Fwd button handler."""
        if self.state == self.PLAYING:
            # send a request for fwd
            print("put the fwd")
            self.sendRtspRequest(self.FWD)

    def playMovie(self):
        """Play button handler."""

        if self.first_play & self.state == self.INIT:
            self.first_play = False
            self.sendRtspRequest(self.SETUP)

        while self.total_frames == 0:
            print("have not get the total frames")
        print("total", self.total_frames)

        while self.state == self.INIT:
            print("state not change")

        if self.state == self.READY:
            # Create a new thread to listen for RTP packets
            threading.Thread(target=self.listenRtp).start()
            self.playEvent = threading.Event()
            self.playEvent.clear()
            self.sendRtspRequest(self.PLAY)

    def listenRtp(self):
        """Listen for RTP packets."""
        # 绘图的话不能点快进快退，不然数据意义不大了
        start_time = time.time()
        while True:
            try:
                data = self.rtpSocket.recv(20480)
                if data:
                    curtime = time.time()
                    one_transimit_Bytes = len(data)
                    self.totalBytes += len(data)
                    total_bytes_list.append((curtime - start_time, self.totalBytes))

                    if time.time() - self.time > 0.1:
                        self.bits_per_second = one_transimit_Bytes * 8 / (time.time() - self.time)
                        # print(f"Bits per second: {self.bits_per_second}")
                        # reset time and number of byte, zsy
                        bits_per_second_list.append((curtime - start_time, self.bits_per_second))

                        one_transimit_Bytes = 0
                        self.time = time.time()
                    rtpPacket = RtpPacket()
                    rtpPacket.decode(data)

                    currFrameNbr = rtpPacket.seqNum()
                    # print("Current self.frame:" + str(self.frameNbr))

                    # by hbh, 5.21, package loss rate
                    # 如果存在回退，那么就不改变丢包率，因为已经收到了；直到帧数大于第一次回退时的frameNbr，才继续改变丢包率
                    if not self.rev:
                        if currFrameNbr - self.frameNbr >= 1:
                            self.packages_loss += currFrameNbr - self.frameNbr - 1
                            packages_loss_list.append((curtime - start_time, self.packages_loss))
                            self.packages_loss_rate = self.packages_loss / currFrameNbr
                            packages_loss_rate_list.append((curtime - start_time, self.packages_loss_rate))

                    elif self.frameNbr >= self.record_rev_frame:
                        self.rev = False
                        if currFrameNbr - self.frameNbr >= 1:
                            self.packages_loss += currFrameNbr - self.frameNbr - 1
                            packages_loss_list.append((curtime - start_time, self.packages_loss))
                            self.packages_loss_rate = self.packages_loss / currFrameNbr
                            packages_loss_rate_list.append((curtime - start_time, self.packages_loss_rate))

                    # 视频播放结束，存储数据
                    if currFrameNbr == 500:
                        with open('total_bytes_list.pickle', 'wb') as f:
                            pickle.dump(total_bytes_list, f)
                        with open('bits_per_second_list.pickle', 'wb') as f:
                            pickle.dump(bits_per_second_list, f)
                        with open('packages_loss_list.pickle', 'wb') as f:
                            pickle.dump(packages_loss_list, f)
                        with open('packages_loss_rate_list.pickle', 'wb') as f:
                            pickle.dump(packages_loss_rate_list, f)

                    if currFrameNbr > self.frameNbr:  # Discard the late packet
                        self.frameNbr = currFrameNbr
                        self.scale.set(self.frameNbr / self.total_frames)
                        self.updateMovie(self.writeFrame(rtpPacket.getPayload()))
            except:
                # Stop listening upon requesting PAUSE or TEARDOWN
                if self.playEvent.isSet():
                    break

                # Upon receiving ACK for TEARDOWN request,
                # close the RTP socket
                if self.teardownAcked == 1:
                    self.rtpSocket.shutdown(socket.SHUT_RDWR)
                    self.rtpSocket.close()

                    break

    def writeFrame(self, data):
        """Write the received frame to a temp image file. Return the image file."""
        cachename = CACHE_FILE_NAME + str(self.sessionId) + CACHE_FILE_EXT
        file = open(cachename, "wb")
        file.write(data)
        file.close()

        return cachename

    def updateMovie(self, imageFile):
        """ Update the image file as video frame in the GUI. """
        self.photo = ImageTk.PhotoImage(Image.open(imageFile))
        self.media.configure(image=self.photo, height=288)

    def connectToServer(self):
        """ Connect to the Server. Start a new RTSP/TCP session. """
        self.rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            self.rtspSocket.connect((self.serverAddr, self.serverPort))
        except:
            showwarning('Connection Failed', 'Connection to \'%s\' failed.' % self.serverAddr)

    '''
		5.6 Zhu Pengxiang: Initial Attempt
		5.21 Hbh: modified DESCRIBE request
	'''

    def sendRtspRequest(self, requestCode):
        """ Send RTSP request to the server. """
        # In this part, we need to refer to the description of the guidebook
        # And the STATE TRANSITION figure, where the states and operations are clearly defined

        # Setup request
        if requestCode == self.SETUP and self.state == self.INIT:
            threading.Thread(target=self.recvRtspReply).start()
            # Update RTSP sequence number.
            self.rtspSeq += 1

            # Write the RTSP request to be sent.
            # The request need to be formulated in the following manner

            # -------ATTENTION!!!!----------#
            # -------!!!!!!!!!!!!!----------#
            # The variable request is CRUCIAL, DO NOT modify the spaces and \n
            # as it will be used for decoding in ServerWorker.py
            # I have modified ServerWorker.py slightly, and it should work fine.

            """
				We need to formulate the message according to ServerWorker.py

				requestType = line1[0]
				filename = line1[1]
				# Get the RTSP sequence number 
				seq = line2.split(' ')

				# Get the RTP/UDP port from the last line
				self.clientInfo['rtpPort'] = request[2].split(' ')[3]
			"""
            request = "SETUP " + str(self.fileName) + "\nCseq: " + str(self.rtspSeq) \
                      + "\n" + "RTSP/1.0 RTP/UDP " + str(self.rtpPort)

            # Keep track of the sent request.
            self.requestSent = self.SETUP

        # Play request
        elif requestCode == self.PLAY and self.state == self.READY:
            # Update RTSP sequence number.
            self.rtspSeq = self.rtspSeq + 1

            # Write the RTSP request to be sent.
            request = "PLAY " + "\nCseq: " + str(self.rtspSeq)

            # Keep track of the sent request.
            self.requestSent = self.PLAY

        # Pause request
        elif requestCode == self.PAUSE and self.state == self.PLAYING:
            # Update RTSP sequence number.
            self.rtspSeq = self.rtspSeq + 1

            # Write the RTSP request to be sent.
            request = "PAUSE " + "\nCseq: " + str(self.rtspSeq)

            # Keep track of the sent request.
            self.requestSent = self.PAUSE

        # Teardown request
        elif requestCode == self.TEARDOWN and not self.state == self.INIT:
            # Update RTSP sequence number.
            self.rtspSeq = self.rtspSeq + 1

            # Write the RTSP request to be sent.
            request = "TEARDOWN " + "\nCseq: " + str(self.rtspSeq)

            # Keep track of the sent request.
            self.requestSent = self.TEARDOWN

        # Describe request
        elif requestCode == self.DESCRIBE and not self.state == self.INIT:
            # Update RTSP sequence number.
            self.rtspSeq = self.rtspSeq + 1

            # Write the RTSP request to be sent.
            request = "DESCRIBE " + str(self.fileName) + "\nCseq: " + str(self.rtspSeq) \
                      + "\n" + "RTSP/1.0 RTP/UDP " + str(self.rtpPort)

            # Keep track of the sent request.
            self.requestSent = self.DESCRIBE


        # FWD request
        elif requestCode == self.FWD:
            # Update RTSP sequence number.
            n = 100
            self.rtspSeq = self.rtspSeq + 1
            # Write the RTSP request to be sent.
            request = "FORWARD " + "\nCseq: " + str(self.rtspSeq)
            # Keep track of the sent request.
            self.requestSent = self.FWD
            self.frameNbr += n


        elif requestCode == self.REV:
            # n is the number of frames which is reversed
            # need to align with the serverWorker's revpoint(n)
            n = 100
            # Update RTSP sequence number.
            self.rtspSeq = self.rtspSeq + 1
            if not self.rev:
                self.rev = True
                self.record_rev_frame = self.frameNbr
            self.frameNbr -= n

            # Write the RTSP request to be sent.
            request = "REVERSE " + "\nCseq: " + str(self.rtspSeq)
            # Keep track of the sent request.
            self.requestSent = self.REV




        else:
            return

        # Send the RTSP request using rtspSocket.
        self.rtspSocket.sendto(str(request).encode(), (self.serverAddr, self.serverPort))

        print('\nData sent:\n' + request)

    def recvRtspReply(self):
        """Receive RTSP reply from the server."""
        while True:

            reply = self.rtspSocket.recv(1024)  # 这里的1024是指一次从RTSP socket中最多接收的字节数
            # print("reply",reply)

            if reply:
                self.parseRtspReply(reply.decode("utf-8"))

            # Close the RTSP socket upon requesting Teardown
            if self.requestSent == self.TEARDOWN:
                self.rtspSocket.shutdown(socket.SHUT_RDWR)
                self.rtspSocket.close()
                break

    '''
	5.6 Zhu Pengxiang: Initial Attempt
	5.21 Hbh: add SDP parse, For DESCRIBE information
	'''

    def parseRtspReply(self, data):  # 这里的data是指从RTSP socket中接收到的数据
        """Parse the RTSP reply from the server."""
        lines = data.split('\n')
        seqNum = int(lines[1].split(' ')[1])

        # Process only if the server reply's sequence number is the same as the request's
        if seqNum == self.rtspSeq:

            session = int(lines[2].split(' ')[1])
            # New RTSP session ID
            if self.sessionId == 0:
                self.sessionId = session

            # Process only if the session ID is the same
            if self.sessionId == session:

                if int(lines[0].split(' ')[1]) == 200:
                    # change the state
                    if self.requestSent == self.SETUP:
                        self.state = self.READY

                        self.total_frames = int(lines[3].split(' ')[1])
                        # self.remain_var.set(self.total_frames)

                        # Open RTP port.
                        self.openRtpPort()

                    elif self.requestSent == self.PLAY:
                        self.state = self.PLAYING
                        # Update buttons' states

                        self.pause_btn["state"] = "normal"
                        self.stop_btn["state"] = "normal"
                        self.rev_btn["state"] = "normal"
                        self.play_btn["state"] = "disabled"


                    elif self.requestSent == self.PAUSE:
                        self.state = self.READY

                        self.pause_btn["state"] = "disabled"
                        self.stop_btn["state"] = "normal"
                        self.rev_btn["state"] = "normal"
                        self.play_btn["state"] = "normal"

                        # The play thread exits. A new thread is created on resume.
                        self.playEvent.set()
                    elif self.requestSent == self.TEARDOWN:
                        self.state = self.INIT

                        # Flag the teardownAcked to close the socket.
                        self.teardownAcked = 1
                    elif self.requestSent == self.DESCRIBE:
                        sdpDescription = data.split('\r\n\r\n')[1]
                        # Process the SDP description, for example, by parsing it
                        self.processSdpDescription(sdpDescription)

    def processSdpDescription(self, sdpDescription):
        """Process the SDP description to get information about the video stream."""

        lines = sdpDescription.split('\r\n')

        for line in lines:
            parts = line.split('=')
            if len(parts) == 2:
                fieldType = parts[0].strip()
                fieldValue = parts[1].strip()

                if fieldType == 'm':
                    # Extract the RTP/AVP payload type, session type
                    self.sessionType = fieldValue.split(' ')[0]
                    self.payloadType = int(fieldValue.split(' ')[-1])
                    # print("Payload type:", payloadType) # 媒体格式, 和session type相关，但不一样！

                elif fieldType == 'a' and fieldValue.startswith('rtpmap'):
                    # Extract the encoding format and clock rate
                    rtpmap_parts = fieldValue.split(' ')[1].split('/')
                    self.encodingFormat = rtpmap_parts[1]
                    # clockRate = int(rtpmap_parts[1]) # 这里的clockRate是指每秒钟的采样次数, 是SDP协议里包含的一个信息
                    # print("Encoding format:", encodingFormat)
                    # print("Clock rate:", clockRate)

        # You can store and use the extracted information (e.g., payloadType, encodingFormat, clockRate) as needed

    def openRtpPort(self):
        """ Open RTP socket binded to a specified port. """
        # Create a new datagram socket to receive RTP packets from the server
        self.rtpSocket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

        # Set the timeout value of the socket to 0.5 sec
        # self.rtspSocket.settimeout(5)

        try:
            # Bind the socket to the address using the RTP port given by the client user
            self.rtpSocket.bind((self.serverAddr, self.rtpPort))
        except:
            showwarning('Unable to Bind', 'Unable to bind PORT=%d' % self.rtpPort)

    def handler(self):
        """ Handler on explicitly closing the GUI window."""
        self.pauseMovie()
        if askokcancel("Quit?", "Are you sure you want to quit?"):
            self.exitClient()
        else:  # When the user presses cancel, resume playing.
            self.playMovie()
