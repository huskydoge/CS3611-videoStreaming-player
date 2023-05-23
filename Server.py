import sys, socket

from ServerWorker import ServerWorker

# These two modules implement the server which responds to the RTSP requests and streams back the video. The RTSP interaction is already implemented and the ServerWorker calls methods from the RtpPacket class to packetize the video data. You do not need to modify these modules.

class Server:

	def main(self): # 从命令行参数获取服务器端口号
		try:
			SERVER_PORT = int(sys.argv[1])
		except:
			print("[Usage: Server.py Server_port]\n")

		# 创建TCP套接字并绑定到指定的IP地址和端口号，然后开始监听客户端连接请求
		# socket.AF_INET表示使用IPv4地址族，socket.SOCK_STREAM表示使用TCP协议提供面向连接的字节流传输。
		rtspSocket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		rtspSocket.bind(('', SERVER_PORT))

		rtspSocket.listen(5)
		# listen(5)是用于监听客户端连接请求的方法，其中的参数5表示在套接字可以开始接受之前，操作系统可以挂起的最大连接数量。
		# 这个值通常设置为一个相对较小的数目，例如5，因为每个等待处理的连接都需要占用一定的系统资源（如内存和CPU时间）。
		# 如果过多地挂起连接，则可能会影响服务器的性能，甚至导致服务器崩溃。当然，也不要将其设置为太小，否则可能会导致某些连接无法及时得到处理。

		# Receive client info (address,port) through RTSP/TCP session
		while True:
			clientInfo = {}
			clientInfo['rtspSocket'] = rtspSocket.accept()
			ServerWorker(clientInfo).run()

if __name__ == "__main__":
	(Server()).main()


