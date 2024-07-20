import cv2
from VideoWriter import get_video_writer
import time
import requests
import json
import shutil
from pathlib import Path
import os

CONFIG_PATH = "./config.json"
fp = open(CONFIG_PATH)
config = json.load(fp)
bayId = config["bayId"]
base_url_tech = config["baseUrlTech"]
file_upload_url_tech = base_url_tech + "/fileStorage/upload"
file_download_endpoint = "/fileStorage/download/"
ECON_CAMERA_CONFIG_PATH = "./CameraParameters/EconCameraConfig.json"
ANIMATIONS_DIR_PATH = os.path.join(bayId, str(config["animationDirectory"]))


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


def recordVideoUsingNetworkCameraWithLogo(videoFolderPath, logoPath, rtspUrl, videoLength):
    # Ensure the video folder exists
    create_folder_if_not_exists(videoFolderPath)

    logo = cv2.imread(logoPath, cv2.IMREAD_UNCHANGED)
    video = cv2.VideoCapture(rtspUrl)
    logo_height, logo_width, _ = logo.shape
    # Define the position of the logo in the top right corner
    logo_margin = 10  # Margin from the video edges
    logo_x = int(video.get(cv2.CAP_PROP_FRAME_WIDTH)) - logo_width - logo_margin
    logo_y = logo_margin

    # Get the video's frames per second (fps) and frame size
    fps = int(video.get(cv2.CAP_PROP_FPS))
    frame_size = (int(video.get(cv2.CAP_PROP_FRAME_WIDTH)), int(video.get(cv2.CAP_PROP_FRAME_HEIGHT)))
    print(frame_size)

    video_writer = get_video_writer(full_path=videoFolderPath, dimensions=frame_size, fps=fps)

    timeout = time.time() + videoLength
    while True:
        success, frame = video.read()

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
            return shortenUrl(fileUrl)
        return None
    except Exception as e:
        print(e)
        return None


def copyAndPasteVideo(src, dst):
    shutil.copy(src, dst)


def checkForFile(filePath):
    path = Path(filePath)
    return path.is_file()


def transferVideoToAllPlayersVideosFolder(all_players_dir_path, current_video_full_path,
                                          current_video_file_name, current_player, current_ball_score):
    create_folder_if_not_exists(all_players_dir_path)
    copyAndPasteVideo(current_video_full_path, all_players_dir_path)
    add_animation_to_video(all_players_dir_path + "/" + current_video_file_name, current_ball_score)
    os.rename(all_players_dir_path + "/" + current_video_file_name,
              all_players_dir_path + "/" + current_player + "_" + current_ball_score + ".avi")


def checkIfBetterShot(all_players_dir_path, current_video_full_path,
                      current_video_file_name, current_player, current_ball_score):
    create_folder_if_not_exists(all_players_dir_path)
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
    create_folder_if_not_exists(all_players_dir_path)
    allVideoIds = []
    for filename in os.listdir(all_players_dir_path):
        videoUrl = uploadVideo(all_players_dir_path + "/" + filename, filename)
        playerVideoInfo = {"playerId": filename.split("_")[1], "videoUrl": videoUrl}
        allVideoIds.append(playerVideoInfo)

        # delete file after uploading because the game is ended.
        # deleteFile(all_players_dir_path + "/" + filename)

    return allVideoIds


def create_folder_if_not_exists(folder_path):
    # Ensure the directory exists or create it if it doesn't
    if not os.path.exists(folder_path):
        os.makedirs(folder_path)


def deleteFile(filePath):
    os.remove(filePath)


def add_animation_to_video(video_path, score):
    for filename in os.listdir(ANIMATIONS_DIR_PATH):
        animation_of_score = filename.split(".")[0]
        if animation_of_score == score:
            merge_videos(video_path, ANIMATIONS_DIR_PATH + "/" + filename, video_path)
            break


def merge_videos(video1_path, video2_path, output_path):
    # Open the first video file
    video1 = cv2.VideoCapture(video1_path)
    if not video1.isOpened():
        print(f"Error: Could not open video file '{video1_path}'")
        return

    # Open the second video file
    video2 = cv2.VideoCapture(video2_path)
    if not video2.isOpened():
        print(f"Error: Could not open video file '{video2_path}'")
        return

    # Get video properties (assuming both videos have the same properties)
    fps = video1.get(cv2.CAP_PROP_FPS)
    width = int(video1.get(cv2.CAP_PROP_FRAME_WIDTH))
    height = int(video1.get(cv2.CAP_PROP_FRAME_HEIGHT))

    out = get_video_writer(full_path=output_path, dimensions=(width, height), fps=fps)

    # Read and write frames from video1
    while True:
        ret, frame = video1.read()
        if ret:
            out.write(frame)
        else:
            break

    # Read and write frames from video2
    while True:
        ret, frame = video2.read()
        if ret:
            out.write(frame)
        else:
            break

    # Release resources
    video1.release()
    video2.release()
    out.release()


def shortenUrl(url):
    payload = {
        "url": url
    }

    # Necessary to get a non-html response
    headers = {
        "Accept": "application/json"
    }

    response = requests.post("https://spoo.me", data=payload, headers=headers)

    if response.status_code == 200:
        # If the request was successful, print the shortened URL
        return response.json().get("short_url")
    else:
        # If the request failed, print the error message
        print(f"Error: {response.status_code}")
        print(response.text)
        return url
