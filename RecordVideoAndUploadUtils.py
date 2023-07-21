import cv2
from VideoWriter import get_video_writer
import time
import requests
import json
import shutil
import os
from pathlib import Path
from Utils.ShellUtils import getSerialNoOfEconCameraByIndex
import os
import numpy as np

CONFIG_PATH = "./config.json"
fp = open(CONFIG_PATH)
config = json.load(fp)
base_url = config["baseUrl"]
base_url_tech = config["baseUrlTech"]
file_upload_url_tech = base_url_tech + "/fileStorage/upload/s3"
file_download_endpoint = "/fileStorage/download/"
ECON_CAMERA_CONFIG_PATH = "./CameraParameters/EconCameraConfig.json"


class PlayerVideoInfo:
    playerId: str
    videoId: str


class EndGameValues:
    videoIds = list


def recordVideo(videoFolderPath):
    cap = cv2.VideoCapture(0)
    fps = int(cap.get(cv2.CAP_PROP_FPS))

    _, frame1 = cap.read()

    video_writer = get_video_writer(full_path=videoFolderPath, dimensions=(frame1.shape[1], frame1.shape[0]), fps=fps)

    timeout = time.time() + 10  # 10 seconds from now
    while True:
        success, frame = cap.read()

        if not success:
            break
        video_writer.write(frame)

        if time.time() > timeout:
            video_writer.release()
            break

    cap.release()
    video_writer.release()


def recordVideoWithLogo(videoFolderPath, logoPath, videoIndex: int):
    camera_serial_number = getSerialNoOfEconCameraByIndex(videoIndex)
    fp = open(ECON_CAMERA_CONFIG_PATH)
    econ_config = json.load(fp)
    camera_position = econ_config[str(camera_serial_number)]["position"]
    print("camera position: " + camera_position)
    distortion_matrix = np.load(econ_config[str(camera_serial_number)]["dist_mat_path"])
    intrinsic_matrix = np.load(econ_config[str(camera_serial_number)]["intrinsic_mat_path"])

    logo = cv2.imread(logoPath, cv2.IMREAD_UNCHANGED)
    video = cv2.VideoCapture(videoIndex)
    logo_height, logo_width, _ = logo.shape
    # Define the position of the logo in the top right corner
    logo_margin = 10  # Margin from the video edges
    logo_x = int(video.get(cv2.CAP_PROP_FRAME_WIDTH)) - logo_width - logo_margin
    logo_y = logo_margin

    # Get the video's frames per second (fps) and frame size
    fps = int(video.get(cv2.CAP_PROP_FPS))
    frame_size = (int(video.get(cv2.CAP_PROP_FRAME_WIDTH)), int(video.get(cv2.CAP_PROP_FRAME_HEIGHT)))

    video_writer = get_video_writer(full_path=videoFolderPath, dimensions=frame_size, fps=fps)

    timeout = time.time() + 11  # 11 seconds from now
    while True:
        success, frame = video.read()
        frame = cv2.undistort(frame, intrinsic_matrix, distortion_matrix)

        if not success:
            break
        # Create a copy of the frame
        frame_with_logo = frame.copy()

        # Get the ROI in the frame for logo placement
        roi = frame_with_logo[logo_y:logo_y + logo_height, logo_x:logo_x + logo_width]

        # Resize the logo image to match the ROI size
        resized_logo = cv2.resize(logo, (roi.shape[1], roi.shape[0]))

        # Extract the alpha channel of the logo
        alpha_channel = resized_logo[:, :, 3] / 255.0

        # Apply the logo on the ROI using alpha blending
        for c in range(0, 3):
            roi[:, :, c] = (1 - alpha_channel) * roi[:, :, c] + alpha_channel * resized_logo[:, :, c]

        # Update the frame with the logo
        frame_with_logo[logo_y:logo_y + logo_height, logo_x:logo_x + logo_width] = roi

        # cv2.imshow("Cam", frame)
        video_writer.write(frame_with_logo)

        if time.time() > timeout:
            break
    video.release()
    video_writer.release()


def uploadVideo(videoPath, videoName):
    parameters = {"payload": '{"bucketName":"VIRTUE_USER_UPLOADS","dirPrefix":"GENERAL_DOCS","purpose":"file upload"}'}
    try:
        response = requests.post(file_upload_url_tech, params=parameters,
                                 files={'file': (videoName, open(videoPath, 'rb'), 'video/x-msvideo')})
        if response.status_code == 200:
            fileId = response.json()["id"]
            fileUrl = base_url_tech + file_download_endpoint + fileId
            return str(fileUrl)
        return None
    except ArithmeticError as e:
        print(e)
        return None


def copyAndPasteVideo(src, dst):
    shutil.copy(src, dst)


def checkForFile(filePath):
    path = Path(filePath)
    return path.is_file()


def transferVideoToAllPlayersVideosFolder(all_players_dir_path, current_video_full_path,
                                          current_video_file_name, current_player, current_ball_score):
    copyAndPasteVideo(current_video_full_path, all_players_dir_path)
    os.rename(all_players_dir_path + current_video_file_name,
              all_players_dir_path + "/" + current_player + "_" + current_ball_score + ".avi")


def checkIfBetterShot(all_players_dir_path, current_video_full_path,
                      current_video_file_name, current_player, current_ball_score):
    file_for_player_exists = False
    for filename in os.listdir(all_players_dir_path):
        name = filename.split(".")[0]
        # File for current player already exists
        if current_player in name:
            file_for_player_exists = True
            run_in_filename = name.split("_")[2]
            if not int(current_ball_score) < int(run_in_filename):
                os.remove(all_players_dir_path + "/" + filename)
                transferVideoToAllPlayersVideosFolder(all_players_dir_path,
                                                      current_video_full_path, current_video_file_name, current_player,
                                                      current_ball_score)

    # file for current player does not exist
    if not file_for_player_exists:
        transferVideoToAllPlayersVideosFolder(all_players_dir_path, current_video_full_path,
                                              current_video_file_name, current_player, current_ball_score)


def getAllPlayerVideoUrls(all_players_dir_path):
    allVideoIds = []
    for filename in os.listdir(all_players_dir_path):
        videoUrl = uploadVideo(all_players_dir_path + filename, filename)
        playerVideoInfo = {"playerId": filename.split("_")[1], "videoUrl": videoUrl}
        allVideoIds.append(playerVideoInfo)

        # delete file after uploading because the game is ended.
        # deleteFile(all_players_dir_path + filename)

    return allVideoIds


def deleteFile(filePath):
    os.remove(filePath)
