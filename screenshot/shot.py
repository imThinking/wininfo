import screenshot as SHOT
import socket


host = (socket.gethostbyname(socket.gethostname()))   # Get IP address
path = SHOT.cur_file_dir() # get current directory
S = SHOT.ScreenShot(host, path) # take a screenshot and save it to file