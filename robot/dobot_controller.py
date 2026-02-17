"""
Dobot MG400 Controller Module
Contains functions for robot connection, movement, and feedback monitoring

Uses Dobot Python API from https://github.com/Dobot-Arm/TCP-IP-4Axis-Python
"""

import socket
import threading
from robot.dobot_api import DobotApiDashboard, DobotApi, DobotApiMove, MyType, alarmAlarmJsonFile
from time import sleep
import numpy as np

# Global variables for robot feedback
current_actual = None
algorithm_queue = None
enableStatus_robot = None
robotErrorState = False
globalLockValue = threading.Lock()
stop_threads = False


def ConnectRobot(ip="192.168.1.6", timeout_s=5.0):
    """
    Establish connection to the Dobot MG400 robot

    Args:
        ip: Robot IP address
        timeout_s: Connection timeout in seconds

    Returns:
        tuple: (dashboard, move, feed) API objects
    """
    try:
        dashboardPort = 29999
        movePort = 30003
        feedPort = 30004
        print("Establishing connection...")
        dashboard = DobotApiDashboard(ip, dashboardPort, timeout_s=timeout_s)
        move = DobotApiMove(ip, movePort, timeout_s=timeout_s)
        feed = DobotApi(ip, feedPort, timeout_s=timeout_s)
        print("Connection successful!")
        return dashboard, move, feed
    except Exception as e:
        print(f"Connection failed: {e}")
        raise e


def GetFeed(feed: DobotApi):
    """
    Continuously read feedback from the robot
    This function should run in a separate thread

    Args:
        feed: DobotApi object for feedback port
    """
    global current_actual, algorithm_queue, enableStatus_robot, robotErrorState, stop_threads
    hasRead = 0

    # Set a timeout on the socket so recv() doesn't block forever
    # This allows the loop to check the 'stop_threads' flag
    feed.socket_dobot.settimeout(1.0)

    while not stop_threads:  # Check the flag here
        try:
            data = bytes()
            while hasRead < 1440 and not stop_threads:
                try:
                    temp = feed.socket_dobot.recv(1440 - hasRead)
                    if len(temp) > 0:
                        hasRead += len(temp)
                        data += temp
                except socket.timeout:
                    # Timeout reached, loop back to check stop_threads
                    continue

            if stop_threads:
                break

            hasRead = 0
            feedInfo = np.frombuffer(data, dtype=MyType)

            if hex((feedInfo['test_value'][0])) == '0x123456789abcdef':
                globalLockValue.acquire()
                current_actual = feedInfo["tool_vector_actual"][0]
                algorithm_queue = feedInfo['isRunQueuedCmd'][0]
                enableStatus_robot = feedInfo['EnableStatus'][0]
                robotErrorState = feedInfo['ErrorStatus'][0]
                globalLockValue.release()
            sleep(0.001)

        except Exception as e:
            if not stop_threads:
                print(f"Feed Error: {e}")
            sleep(0.1)


def StartFeedbackThread(feed: DobotApi):
    """
    Start the feedback monitoring thread

    Args:
        feed: DobotApi object for feedback port

    Returns:
        threading.Thread: The started thread object
    """
    feed_thread = threading.Thread(target=GetFeed, args=(feed,))
    feed_thread.daemon = True
    feed_thread.start()
    print("Feedback thread started")
    sleep(1)  # Give feedback thread time to initialize
    return feed_thread


def WaitArrive(target_point, tolerance=1.0, timeout=30.0):
    """
    Wait until the robot reaches the target point

    Args:
        target_point: [x, y, z, r] coordinates
        tolerance: acceptable position error in mm
        timeout: maximum wait time in seconds

    Returns:
        bool: True if robot arrived, False if timeout
    """
    print(f"Waiting for robot to reach target: {target_point}")
    start_time = sleep(0)  # Using sleep to track time
    elapsed = 0

    while elapsed < timeout:
        is_arrive = True
        globalLockValue.acquire()
        if current_actual is not None:
            # Check if all coordinates are within tolerance
            for index in range(4):
                if abs(current_actual[index] - target_point[index]) > tolerance:
                    is_arrive = False
                    break

            if is_arrive:
                globalLockValue.release()
                print("Robot reached target position!")
                return True
        globalLockValue.release()
        sleep(0.001)
        elapsed += 0.001

    print(f"Timeout: Robot did not reach target within {timeout}s")
    return False


def MoveJ(move: DobotApiMove, point):
    """
    Move robot to specified point using Joint movement

    Args:
        move: DobotApiMove object
        point: [x, y, z, r] coordinates
    """
    print(f"Moving to point: {point}")
    move.MovJ(point[0], point[1], point[2], point[3])


def MoveL(move: DobotApiMove, point):
    """
    Move robot to specified point using Linear movement

    Args:
        move: DobotApiMove object
        point: [x, y, z, r] coordinates
    """
    print(f"Moving to point: {point}")
    move.MovL(point[0], point[1], point[2], point[3])


def SetupRobot(dashboard: DobotApiDashboard, speed_ratio=50, acc_ratio=50, payload_weight=50):
    """
    Initialize and configure the robot

    Args:
        dashboard: DobotApiDashboard object
        speed_ratio: Speed ratio percentage (1-100)
        acc_ratio: Acceleration ratio percentage (1-100)
        payload_weight: Payload weight (in grams) (0-750)
    """
    print("Clearing any errors...")
    dashboard.ClearError()
    sleep(0.5)

    print("Enabling robot...")
    dashboard.EnableRobot()
    sleep(2)

    # Set speed and acceleration ratios
    print(
        f"Setting speed parameters (speed: {speed_ratio}%, acc: {acc_ratio}%)...")
    dashboard.SpeedJ(speed_ratio)  # Joint speed ratio
    dashboard.SpeedL(speed_ratio)  # Linear speed ratio
    dashboard.AccJ(acc_ratio)      # Joint acceleration
    dashboard.AccL(acc_ratio)      # Linear acceleration

    dashboard.PayLoad(payload_weight, 0)

    print("Robot setup complete!")


def ControlDigitalOutput(dashboard: DobotApiDashboard, output_index, status):
    """
    Control digital output

    Args:
        dashboard: DobotApiDashboard object
        output_index: Digital output index (1-24)
        status: 0 (LOW) or 1 (HIGH)

    Returns:
        str: Command result from robot
    """
    print(f"Setting DO{output_index} to {status}")
    result = dashboard.DO(output_index, status)
    print(f"DO command result: {result}")
    return result


def GetCurrentPosition():
    """
    Get the current robot position from feedback

    Returns:
        numpy.ndarray or None: Current [x, y, z, r, rx, ry] position
    """
    globalLockValue.acquire()
    pos = current_actual
    globalLockValue.release()
    return pos


def DisconnectRobot(dashboard, move, feed, feed_thread=None):
    """
    Safely disconnect from the robot

    Args:
        dashboard: DobotApiDashboard object
        move: DobotApiMove object
        feed: DobotApi object
    """
    global stop_threads
    print("Stopping feedback thread...")
    stop_threads = True  # Signal the thread to stop

    if feed_thread:
        feed_thread.join(timeout=2.0)  # Wait for thread to finish

    print("Disconnecting from robot...")
    try:
        dashboard.DisableRobot()
        sleep(0.5)
    except:
        pass

    dashboard.close()
    move.close()
    feed.close()
    print("Disconnected successfully")