import cv2
import argparse
import numpy as np
import os
from perception.detector import Detector
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
    args = parser.parse_args()

    #create output directory if it doesn't exist
    # if not os.path.exists(OUTPUT_DIR):
    #     os.makedirs(OUTPUT_DIR)

    try:
        H = load_calibration(os.path.join(BASE_DIR, "calibration.json"))
        print(f"Loaded homography matrix:\n{H}")
    except Exception as e:
        print(f"Error loading calibration: {e}")
        return
    
    
    # take image from camera and if failed then read from file
    camera = Camera()
    image = camera.capture_image()
    if image is None:
        print("Failed to capture image from camera. Reading from file...")
        image_path = os.path.join(OUTPUT_DIR, "camera_detection.png")
        image = cv2.imread(image_path)
        if image is None:
            print("Failed to read image from file. Exiting.")
            return
        else:
            print(f"Successfully read image from {image_path}")

        #copy of annotated image for plotting

        display_img = image.copy()

        # detect objects
        detector = Detector()
        detected_objects = detector.find_objects(image, args.color, args.shape)

        target_positions = []
        print(f"\n--- RESULTS ({args.mode.upper()} MODE) ---")

        if not detected_objects:
            print("No objects detected matching the criteria.")

        for obj in detected_objects:
            u, v = obj["pixel_center"]
            shape_type = obj["shape"]

            #coordinates transformation
            rx, ry = pixel_to_robot(u, v, H)
            target_positions.append((rx, ry))

            #annotation

            cv2.circle(display_img, (u, v), 6, (0, 0, 255), 2)
            text = f"{shape_type} (X:{rx:.1f}, Y:{ry:.1f})"
            cv2.putText(display_img, text, (u + 15, v - 15), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 0, 0), 2)

            print(f"Detected {shape_type} at pixel ({u}, {v}) -> Robot (X: {rx:.1f}, Y: {ry:.1f})")

        #save annotated image
        cv2.imwrite(os.path.join(OUTPUT_DIR, "annotated_detections.png"), display_img)
        print(f"Annotated image saved to {os.path.join(OUTPUT_DIR, 'annotated_detections.png')}")

        #Execute robot commands if in execute mode

        if args.mode == "execute" and target_positions:
            robot = DobotController()

            for x, y in target_positions:
                robot.pick_and_place(x, y)
            
            robot.disconnect()

        elif args.mode == "execute":
            print("No target positions to execute. Exiting.")

if __name__ == "__main__":
    main()