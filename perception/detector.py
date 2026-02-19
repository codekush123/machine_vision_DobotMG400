import cv2
import numpy as np
import matplotlib.pyplot as plt

class Detector:
    def __init__(self):

        self.colors = {
            #make red color brighter by increasing the lower bound of saturation and value
            # 
            "red": ([0, 150, 150], [10, 255, 255]),
            "green": ([40, 100, 100], [80, 255, 255]),
            "blue": ([100, 100, 100], [140, 255, 255])
        }

    def find_objects(self, image, color_name="any", shape_type="any"):
        #convert the image to HSV
        hsv = cv2.cvtColor(image, cv2.COLOR_BGR2HSV)
        

        #create a mask for the specified color
        if color_name in self.colors:
            lower, upper = self.colors[color_name]
            mask = cv2.inRange(hsv, np.array(lower), np.array(upper))
        else:
            gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
            _, mask = cv2.threshold(gray, 125, 255, cv2.THRESH_BINARY_INV)
            cv2.imshow("Initial Mask", mask)
            cv2.waitKey(0)


        #morphology

        kernel = np.ones((5, 5), np.uint8)
        mask = cv2.morphologyEx(mask, cv2.MORPH_OPEN, kernel)

        #find contours
        contours , _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)

        detected_objects = []
        for count in contours:
            area = cv2.contourArea(count)
            if area < 500:
                continue

            # circularity
            perimeter = cv2.arcLength(count, True)
            if perimeter > 0:
                circularity = (4 * np.pi * area ) / (perimeter ** 2)
            else:
                circularity = 0

            detected_shape = "circle" if circularity > 0.8 else "square"

            if shape_type != "any" and detected_shape != shape_type:
                continue

            M = cv2.moments(count)
            if M["m00"] != 0:
                u = int(M["m10"] / M["m00"])
                v = int(M["m01"] / M["m00"])
                detected_objects.append({"pixel_center": (u, v), "Shape": detected_shape,  "color": color_name})


        return detected_objects


