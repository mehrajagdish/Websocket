import cv2


def get_video_writer(full_path, dimensions, fps: float):
    fourcc = cv2.VideoWriter_fourcc(*'mp4v')
    out = cv2.VideoWriter(full_path, fourcc, fps, dimensions)
    return out
