import cv2


def get_video_writer(full_path, dimensions, fps: int):
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter(full_path, fourcc, fps, dimensions)
    return out
