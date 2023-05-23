import sys
from tkinter import Tk
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from ttkbootstrap.icons import Emoji
from Client_newUI import Client

# no need for modification!

# The ClientLauncher starts the Client and the user interface which you use to send RTSP commands and which is used to display the video. 
# No need for modification, simply a starter


if __name__ == "__main__":
    try:
        serverAddr = sys.argv[1]
        serverPort = sys.argv[2]
        rtpPort = sys.argv[3]
        fileName = sys.argv[4]
    except:
        print("[Usage: ClientLauncher.py Server_name Server_port RTP_port Video_file]\n")

    root = ttk.Window("RTP Video Player", "yeti")
    # root.iconphoto('/Users/husky/Desktop/blt.png')

    # Create a new client
    app = Client(root, serverAddr, serverPort, rtpPort, fileName)
    root.mainloop()
