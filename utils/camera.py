import cv2


class Camera:
    def __init__(self, index=1):
        self.cam = cv2.VideoCapture(index)
        self.cam.set(cv2.CAP_PROP_FRAME_WIDTH, 1920)
        self.cam.set(cv2.CAP_PROP_FRAME_HEIGHT, 1080)

    def capture_image(self):
        ret, frame = self.cam.read()
        # release immediately to free camera resource
        self.cam.release()

        if not ret or frame is None:
            print("failed to grab frame from camera")
            return None

        # ensure outputs directory exists and save a copy
        try:
            import os
            base_dir = os.path.dirname(os.path.dirname(__file__))
            out_dir = os.path.join(base_dir, "outputs")
            os.makedirs(out_dir, exist_ok=True)
            img_name = os.path.join(out_dir, "camera_detection.png")
            cv2.imwrite(img_name, frame)
        except Exception:
            # ignore save errors but continue returning the frame
            pass

        return frame