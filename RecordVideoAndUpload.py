import cv2
from VideoWriter import get_video_writer
import time
import requests
import json


CONFIG_PATH = "./config.json"

def recordVideo(videoFolderPath):
    cap = cv2.VideoCapture(0)

    _, frame1 = cap.read()

    video_writer = get_video_writer(path=videoFolderPath, dimensions=(frame1.shape[1], frame1.shape[0]))

    timeout = time.time() + 10  # 10 seconds from now
    while True:
        success, frame = cap.read()

        if success:
            # cv2.imshow("Cam", frame)
            video_writer.write(frame)

        if time.time() > timeout:
            video_writer.release()
            break


def uploadVideo(recorderVideoPath):
    fp = open(CONFIG_PATH)
    config = json.load(fp)
    base_url = config["upload-api-base-url"]
    api_url = base_url+"/v-api/fileStorage/upload"
    parameters = {"payload": '{"bucketName":"VIRTUE_USER_UPLOADS","dirPrefix":"GENERAL_DOCS","purpose":"file upload"}'}
    try:
        response = requests.post(api_url, params=parameters,
                                 files={'file': ("video.avi", open(recorderVideoPath, 'rb'), 'video/x-msvideo')})
        if response.status_code == 200:
            fileId = response.json()["id"]
            return str(fileId)
        return None
    except Exception:
        return None


def recordVideoAndUpload():
    recordVideo("Videos/")
    uploadVideo("./Videos/video.avi")
