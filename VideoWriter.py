import cv2
import time


def get_video_writer(path, dimensions):
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(path + "video" + ".avi", fourcc, 20.0, dimensions)
    return out
