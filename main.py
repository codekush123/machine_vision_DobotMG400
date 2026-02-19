import cv2
import argparse
import numpy as np
import os
from perception.detector import Detector
from utils.camera import Camera
from utils.map import load_calibration, pixel_to_robot
from robot.main import DobotController
from utils.camera import Camera

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
OUTPUT_DIR = os.path.join(BASE_DIR, "outputs")

def main():
    #CLI argument parsing
    parser = argparse.ArgumentParser(description="Dobot MG400 Object Detection and Pick-and-Place")
    parser.add_argument("--mode", choices=["plan", "execute"], required=True, help="Mode to run: 'plan' to detect and plan, 'execute' to run the robot")
    parser.add_argument("--color", type=str, default="any", help="Color to detect: 'red', 'green', 'blue', or 'any'")
    parser.add_argument("--shape", type=str, default="any", help="Shape to detect: 'circle', 'square', or 'any'")
    parser.add_argument("--input", type=str, default=None, help="Path to an input image file to process instead of using the camera")
    args = parser.parse_args()


    try:
        H = load_calibration("calibration.json")
        print(f"Loaded homography matrix:\n{H}")
    except Exception as e:
        print(f"Error loading calibration: {e}")
        return
    
    
    
    if args.input:
        if not os.path.exists(args.input):
            print(f"Input image not found: {args.input}")
            return None
        image = cv2.imread(args.input)
        if image is None:
            print(f"Failed to read input image: {args.input}")
            return None
    else:
        image_path = os.path.join(OUTPUT_DIR, "last_capture.jpg")
        if not os.path.exists(image_path):
            print(f"Fallback image not found: {image_path}")
            return None
        image = cv2.imread(image_path)
        if image is None:
            print(f"Failed to read fallback image: {image_path}")
            return None

    def run_detection_and_process(img):
        display_img = img.copy()
        detector = Detector()
        detected_objects = detector.find_objects(display_img, args.color, args.shape)

        target_positions = []
        print(f"\n({args.mode.upper()} MODE)")

        if not detected_objects:
            print("No objects detected.")

        for obj in detected_objects:
            u, v = obj["pixel_center"]
            shape_type = obj["Shape"]

            #coordinates transformation
            rx, ry = pixel_to_robot(u, v, H)
            target_positions.append((rx, ry))

            #annotation
            cv2.circle(display_img, (u, v), 6, (0, 0, 255), 2)
            text = f"{shape_type} (X:{rx:.1f}, Y:{ry:.1f})"
            cv2.putText(display_img, text, (u + 10, v - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

            print(f"Detected {shape_type} at pixel coordinates ({u}, {v}) -> Robot ccordinates (X: {rx:.1f}, Y: {ry:.1f})")

        #save annotated image
        os.makedirs(OUTPUT_DIR, exist_ok=True)
        annotated_path = os.path.join(OUTPUT_DIR, "annotated_detections.png")
        cv2.imwrite(annotated_path, display_img)
        print(f"Annotated image saved to {annotated_path}")

        # display annotated image to the user
        try:
            cv2.imshow("Annotated Detections", display_img)
            print("Press any key in the image window to continue...")
            cv2.waitKey(0)
            cv2.destroyAllWindows()
        except Exception as e:
            print(f"Unable to display image window: {e}")
            pass

        #Execute robot commands if in execute mode
        if args.mode == "execute" and target_positions:
            robot = DobotController()
            for x, y in target_positions:
                robot.pick_and_place(x, y)
            robot.disconnect()
        elif args.mode == "execute":
            print("No target positions to execute. Exiting.")

        return detected_objects, display_img

    # if camera failed entirely, exit (do not use fallback image)
    if image is None:
        print("Failed to capture image from camera. Exiting.")
        return None

    # run detection on camera image and return (do not fallback on empty detections)
    detected_objects, annotated = run_detection_and_process(image)
    return annotated

if __name__ == "__main__":
    main()