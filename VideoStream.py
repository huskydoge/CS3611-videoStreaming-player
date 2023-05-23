from collections import deque


# This class is used to read video data from the file on disk. You do not need to modify this class.
class VideoStream:
    def __init__(self, filename):
        self.filename = filename
        # stack store the length of frames
        self.data_length_stack = deque()
        try:
            self.file = open(filename, 'rb')
        except:
            raise IOError
        self.frameNum = 0

        # 统计总的帧数
        self.total_frameNum = 0
        tmp_length = self.file.read(5)  # Get the framelength from the first 5 bits

        while tmp_length:
            framelength = int(tmp_length)
            # Read the current frame
            self.file.seek(framelength, 1)

            self.total_frameNum += 1
            tmp_length = self.file.read(5)
        self.file.seek(0, 0)

    def get_total_frames_num(self):
        return self.total_frameNum

    def nextFrame(self):
        """Get next frame."""
        data = self.file.read(5)  # Get the framelength from the first 5 bits

        if data:
            framelength = int(data)
            self.data_length_stack.append(framelength)

            # Read the current frame
            data = self.file.read(framelength)

            self.frameNum += 1
        return data

    def movepoint(self, n):
        for i in range(n):
            data = self.file.read(5)
            if data:
                framelength = int(data)
                self.data_length_stack.append(framelength)
                data = self.file.seek(framelength, 1)
                self.frameNum += 1

    def revpoint(self, n):
        framelengths = 0
        for i in range(n):
            if self.frameNum == 3:
                break
            framelength = self.data_length_stack.pop()
            framelengths += (framelength + 5)
            self.frameNum -= 1

        self.file.seek(-framelengths, 1)

    def frameNbr(self):
        """Get frame number."""
        return self.frameNum

    def get_filename(self):
        return self.filename
