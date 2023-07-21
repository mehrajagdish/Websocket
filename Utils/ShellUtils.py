import subprocess


def set_exposure(camera_index, exposure, is_manual):
    # set the exposure after opening the capture to
    # avoid opencv modifying settings
    if is_manual:
        command = "v4l2-ctl -d " + str(camera_index) + \
                  " -c auto_exposure=1 -c exposure_time_absolute=" + str(exposure)
    else:
        command = "v4l2-ctl -d " + str(camera_index) + " -c auto_exposure=0"
    # will return zero if executed successfully
    return subprocess.call(command, shell=True)


def set_fps(camera_index, fps):
    command = " v4l2-ctl -d /dev/video"+str(camera_index)+" --set-parm="+str(fps)
    # will return zero if executed successfully
    subprocess.call(command, shell=True)


def getSerialNoOfEconCameraByIndex(camera_index):
    command = 'udevadm info --query=all --name=/dev/video' + str(camera_index) + ' | grep -oP "(?<=ID_SERIAL_SHORT=).*"'
    serial_number = subprocess.check_output(command, shell=True, universal_newlines=True).strip()
    return serial_number
