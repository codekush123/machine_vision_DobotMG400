from robot.dobot_controller import (
    ConnectRobot,
    StartFeedbackThread,
    SetupRobot,
    MoveJ,
    MoveL,
    WaitArrive,
    ControlDigitalOutput,
    GetCurrentPosition,
    DisconnectRobot
)
from time import sleep
ROBOT_IP = "192.168.1.6"

class DobotController:
    def __init__(self, ip=ROBOT_IP):
        self.ip = ip
        self.safe_z = -75.0
        self.pick_z = -165.0
        self.place_z = -125.0
        self.safe_r = 0

        # drop box location (Coordinates)
        self.drop_location = [275, -125, -75]
        self.dashboard, self.move, self.feed = ConnectRobot(ip=ROBOT_IP, timeout_s=5.0)
        self.feed_thread = StartFeedbackThread(self.feed)

        #setup and enable robot (define the speed and acceleration ratio)

        SetupRobot(self.dashboard, speed_ratio=50, acc_ratio=50)
        print(f"Connecting to robot at {self.ip}")

    def pick_and_place(self, target_x, target_y):
        print(f"Starting pick and place at ({target_x:.1f}, {target_y:.1f})")

        print(f"Moving to Hover: {target_x, target_y, self.safe_z}")
        MoveJ(self.move, [target_x, target_y, self.safe_z, self.safe_r])
        sleep(1)

        print(f"Moving to Pick the object: {target_x, target_y, self.pick_z}")
        MoveL(self.move, [target_x, target_y, self.pick_z, self.safe_r])

        arrived = True
        if arrived:
            print(f"Arrived at the pick location, activating suction")
            ControlDigitalOutput(self.dashboard, output_index=1, status=1)
            sleep(1)

            current_pos = GetCurrentPosition()

            print(f"Robot is at position: {current_pos}")

        else:
            print("Failed to arrive at the pick Location")

        #lifting back to safe height
        print("Lifting")
        MoveL(self.move, [target_x, target_y, self.safe_z, self.safe_r])

        sleep(1)

        #move to drop location
        px, py, pz = self.drop_location
        print(f"Moving to Box at the drop location: {self.drop_location}")
        MoveJ(self.move, [px, py, self.safe_z, self.safe_r])
        sleep(1)

        #descend to place the object
        px, py, pz = self.drop_location
        print(f"Moving to box at {px, py, self.place_z}")
        MoveL(self.move, [px, py, self.place_z, self.safe_r])
        sleep(1)


        arrived = True
        if arrived:
            print(f"Move to drop location, deactivating suction")

        else:
            print("Failed to arrive at the drop Location")

        #turn off digital output to release the object

        print("Releasing the object")
        ControlDigitalOutput(self.dashboard, output_index=1, status=0)
        ControlDigitalOutput(self.dashboard, output_index=2, status=1)
        sleep(1)
        ControlDigitalOutput(self.dashboard, output_index=2, status=0)
        sleep(1)
        print("Pick and place operation completed")


    def disconnect(self):
        print("Disconnecting from robot")
        DisconnectRobot(self.dashboard, self.move, self.feed, self.feed_thread)
