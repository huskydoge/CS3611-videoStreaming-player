import sys
from time import time

HEADER_SIZE = 12


# This class is used to handle the RTP packets. It has separate methods for handling the received packets at the client side and you do not need to modify them. The Client also de-packetizes (decodes) the data and you do not need to modify this method. You will need to complete the implementation of video data RTPpacketization (which is used by the server).

class RtpPacket:
    header = bytearray(HEADER_SIZE)

    def __init__(self):
        pass

    '''
		5.6 Zhu Pengxiang: Initial Attempt
	'''

    def encode(self, version, padding, extension, cc, seqnum, marker, pt, ssrc, payload):
        """ Encode the RTP packet with header fields and payload. """

        timestamp = int(time())
        header = bytearray(HEADER_SIZE)

        # Fill the header bytearray with RTP header fields
        # In fact, nearly all the values for the encode function are specified
        # Refer to makeRtp() method of ServerWork.py for more details

        # An important part in this function is how to handle bytes
        # Here I employed the following approach (might be similar to that in Verilog)

        header[0] = (version << 6) | (padding << 5) | (extension << 4) | cc
        header[1] = marker << 7 | pt
        header[2:4] = seqnum.to_bytes(2, byteorder='big')  # big represents [big end] coding
        header[4:8] = timestamp.to_bytes(4, byteorder='big')
        header[8:12] = ssrc.to_bytes(4, byteorder='big')

        self.header = header

        # Get the payload from the argument
        self.payload = payload

    def decode(self, byteStream):
        """ Decode the RTP packet. """
        self.header = bytearray(byteStream[:HEADER_SIZE])
        self.payload = byteStream[HEADER_SIZE:]

    def version(self):
        """ Return RTP version. """
        return int(self.header[0] >> 6)

    def seqNum(self):
        """ Return sequence (frame) number. """
        seqNum = self.header[2] << 8 | self.header[3]
        return int(seqNum)

    def timestamp(self):
        """ Return timestamp. """
        timestamp = self.header[4] << 24 | self.header[5] << 16 | self.header[6] << 8 | self.header[7]
        return int(timestamp)

    def payloadType(self):
        """ Return payload type. """
        pt = self.header[1] & 127
        return int(pt)

    def getPayload(self):
        """ Return payload. """
        return self.payload

    def getPacket(self):
        """ Return RTP packet. """
        return self.header + self.payload
