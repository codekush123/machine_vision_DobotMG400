import cv2
import matplotlib.pyplot as plt
import numpy as np
import os

# Get the directory where app_streamlit.py is located
current_dir = os.path.dirname(__file__)
# Go up one level to the project root, then into 'outputs'
OUTPUT_FOLDER = os.path.join(current_dir, "..", "outputs")
image_path = os.path.join(OUTPUT_FOLDER, "camera_detection.png")

img = cv2.imread(image_path, cv2.IMREAD_GRAYSCALE)

_, th = cv2.threshold(img, 125, 255, cv2.THRESH_BINARY_INV)

kernel = np.ones((5, 5), np.uint8)
mask = cv2.morphologyEx(th, cv2.MORPH_OPEN, kernel)

plt.subplot(1, 2, 1)
plt.imshow(th, cmap='gray')
plt.title("thresholded")
plt.axis('off')
plt.subplot(1, 2, 2)
plt.imshow(mask, cmap='gray')
plt.title("mask")
plt.axis('off')
plt.show()