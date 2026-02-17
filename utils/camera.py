import cv2


class Camera:
    def __init__(self, index=0):
        self.cam = cv2.VideoCapture(index)
        self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    def get_frame(self):
        ret, frame = self.cam.read()
        if not ret:
            print("failed to grab frame")

        img_name = "outputs/camera_detection.png"
        cv2.imwrite(img_name, frame)

        self.cam.release()