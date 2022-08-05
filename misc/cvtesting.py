import cv2
import numpy as np

im = cv2.imread("trace_test.bmp", cv2.IMREAD_GRAYSCALE)
array = im.astype(np.uint8)

print("ya")
contours, h = cv2.findContours(array, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
print("yeet")

new_image = np.ndarray(cv2.imread("trace_test.bmp").shape)

counter = 0
print(len(contours), h)
for contour in contours:
    for point in contour:
        color = np.array([0,0,0])
        color[2-counter%3] = 255
        new_image[point[0][1], point[0][0]] += color
    counter += 1

cv2.imwrite("trace_testing_contours.bmp", new_image)