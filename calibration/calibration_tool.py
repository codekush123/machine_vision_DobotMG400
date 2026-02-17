import cv2
import numpy as np
import json
import os

img_pts= []

def mouse_click(event, x, y, flags, param):
    if event == cv2.EVENT_LBUTTONDOWN:
        img_pts.append([x, y])
        print(f"Clicked at: ({x}, {y})")

def calibration():

    curr_dir = os.path.dirname(__file__)
    OUTPUT_FOLDER = os.path.join(curr_dir, "..", "outputs")
    image_path = os.path.join(OUTPUT_FOLDER, "last_capture.jpg")

    # first step: read image

    img = cv2.imread(image_path)
    cv2.imshow("Callibrat the image by clicking 4 points", img)
    cv2.setMouseCallback("Callibrat the image by clicking 4 points", mouse_click)
    cv2.waitKey(0)

    if len(img_pts) < 4:
        print("Please click atleast 4 points for the successful calibration")
        return
    
    robot_pts = []
    for i in range(len(img_pts)):
        print(f"Pixel point: {img_pts[i]}")
        rx = float(input("Enter the corresponding robot x coordinate: "))
        ry = float(input("Enter the corresponding robot y coordinate: "))
        robot_pts.append([rx, ry])

    
    #compute the homography matrix
    H, _ = cv2.findHomography(np.array(img_pts), np.array(robot_pts))

    # save the homography to json file

    homography_data = {
        "homography_matrix": H.tolist(),
        "image_size": [img.shape[1], img.shape[0]]}
    
    with open("callibration.json", "w") as f:
        json.dump(homography_data, f)
    print("Calibration successful! Homography matrix saved to callibration.json")


if __name__ == "__main__":
    calibration()