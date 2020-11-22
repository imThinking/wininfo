__title__ = 'wininfo'
__version__ = '0.1'
__author__ = 'ZHOU'
__license__ = 'Apache v2.0 License'
__name__="SnapShot Full Screen"

import win32gui, win32print, win32con, sys, os.path, time, socket
from PIL import ImageGrab

class ScreenShot():
    def __init__(self, HOSTNAME, FILE_PATH):
        self.HOSTNAME = HOSTNAME
        self.FILE_PATH = FILE_PATH

        self.FULLNAME = self.img_fullname()
        self.img_save()

    def get_real_resolution(self):
        # 获取真实的分辨率
        # 避免高分屏因为Windows系统放大像素导致的错误
        hDC = win32gui.GetDC(0)
        # 横向分辨率
        w = win32print.GetDeviceCaps(hDC, win32con.DESKTOPHORZRES)
        # 纵向分辨率
        h = win32print.GetDeviceCaps(hDC, win32con.DESKTOPVERTRES)
        return w, h
    
    def img_save(self):
        # 开始截图，并保存为JPG格式
        # 默认尺寸为全屏
        FILE_NAME = self.FULLNAME
        size = self.get_real_resolution()
        img = ImageGrab.grab(bbox=(0, 0, size[0], size[1]))
        if FILE_NAME != "":
            img.save(FILE_NAME, quality=95)
            print("Successfully saved screenshot: %s" % FILE_NAME)
            return 0
        else:
            print("目录为空！")
            return 1

    def img_fullname(self):
        # 文件名：日期_时间_时间戳.jpg
        # 时间仅取到秒，防止快速截屏覆盖，文件名加入时间戳，精确到毫秒
        rand = "_"+str(int(time.time()*1000))
        FULLNAME = os.path.join(self.FILE_PATH, self.HOSTNAME + "_" + time.strftime("%Y%m%d_%H%M%S", time.localtime(time.time())) + rand + ".jpg")
        return FULLNAME

#获取脚本文件的当前路径
def cur_file_dir():
    path = sys.path[0]
    # 判断为脚本文件还是py2exe编译后的文件，
    # 如果是脚本文件，则返回的是脚本的目录，
    # 如果是py2exe编译后的文件，则返回的是编译后的文件路径
    if os.path.isdir(path):
        return path
    elif os.path.isfile(path):
        return os.path.dirname(path)
    path = sys.path

if __name__ == "__main__":
    host = (socket.gethostbyname(socket.gethostname())) 
    path = cur_file_dir()
    S = ScreenShot(host, path)