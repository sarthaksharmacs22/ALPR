import cv2
from plate_recognition import PlateRecognizer

recognizer = PlateRecognizer()
image = cv2.imread("test_plate.jpg")  # Replace with a clear plate image
plate = recognizer.recognize_plate(image)
print("Detected Plate:", plate)
