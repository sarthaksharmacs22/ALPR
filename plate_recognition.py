""""
import cv2
import numpy as np
import pytesseract
from config import PLATE_MIN_AREA, PLATE_RATIO, DEBUG_MODE, SAVE_IMAGES
from datetime import datetime
import os

class PlateRecognizer:
    def __init__(self):
        pytesseract.pytesseract.tesseract_cmd = r'"C:\Tesseract-OCR\tesseract.exe"'  # Update this path
        
    def preprocess_image(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        edged = cv2.Canny(blur, 50, 200)
        return edged
    
    def find_plate_contours(self, img):
        contours, _ = cv2.findContours(img.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]
        
        plate_contours = []
        for contour in contours:
            approx = cv2.approxPolyDP(contour, 0.02 * cv2.arcLength(contour, True), True)
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / float(h)
                
                if (w * h > PLATE_MIN_AREA) and (2.5 < aspect_ratio < PLATE_RATIO):
                    plate_contours.append(contour)
        
        return plate_contours
    
    def recognize_plate(self, img):
        processed = self.preprocess_image(img)
        plate_contours = self.find_plate_contours(processed)
        
        if not plate_contours:
            return None
        
        # Get the largest plate contour
        plate_contour = max(plate_contours, key=cv2.contourArea)
        x, y, w, h = cv2.boundingRect(plate_contour)
        
        # Crop and process plate region
        plate_img = img[y:y+h, x:x+w]
        plate_gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
        _, plate_thresh = cv2.threshold(plate_gray, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)
        
        # OCR processing
        custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
        plate_text = pytesseract.image_to_string(plate_thresh, config=custom_config)
        plate_text = ''.join(e for e in plate_text if e.isalnum())
        
        if DEBUG_MODE:
            cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
            cv2.putText(img, plate_text, (x, y - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            cv2.imshow('Processed', img)
            
        if SAVE_IMAGES and plate_text:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            cv2.imwrite(f"captures/{plate_text}_{timestamp}.jpg", img)
            
        return plate_text if plate_text else None
"""

import cv2
import numpy as np
import pytesseract
from config import PLATE_MIN_AREA, PLATE_RATIO, DEBUG_MODE, SAVE_IMAGES
from datetime import datetime
import os

class PlateRecognizer:
    def __init__(self):
        # Verify Tesseract path exists (common installation locations)
        possible_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Tesseract-OCR\tesseract.exe"
        ]
        for path in possible_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                break
        else:
            raise FileNotFoundError("Tesseract OCR not found. Please install it.")
    
    def preprocess_image(self, img):
        #Enhanced preprocessing with multiple techniques
        # Convert to grayscale
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Noise reduction
        blur = cv2.bilateralFilter(gray, 11, 17, 17)
        
        # Edge detection with adaptive thresholds
        v = np.median(blur)
        lower = int(max(0, (1.0 - 0.33) * v))
        upper = int(min(255, (1.0 + 0.33) * v))
        edged = cv2.Canny(blur, lower, upper)
        
        # Morphological operations to close gaps
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        edged = cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)
        
        return edged
    
      
    def find_plate_contours(self, edged, img):
        """More robust contour detection with validation checks"""
        contours, _ = cv2.findContours(edged.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        contours = sorted(contours, key=cv2.contourArea, reverse=True)[:10]  # Limit to top 10
        
        plate_contours = []
        for contour in contours:
            # Approximate the contour
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            
            # Look for rectangular contours
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / float(h)
                area = w * h
                
                # Validate based on aspect ratio and area
                if (area > PLATE_MIN_AREA and 
                    2.0 < aspect_ratio < PLATE_RATIO):
                    plate_contours.append((x, y, w, h))
                    
                    if DEBUG_MODE:
                        cv2.drawContours(img, [approx], -1, (0, 255, 0), 2)
        
        return plate_contours if plate_contours else None
      
      
    def recognize_plate(self, img):
        #Complete plate recognition pipeline with error handling
        try:
            processed = self.preprocess_image(img)
            plate_coords = self.find_plate_contours(processed, img)
            
            if not plate_coords:
                if DEBUG_MODE:
                    print("[DEBUG] No plate contours found")
                return None
            
            # Get the largest plate candidate
            x, y, w, h = max(plate_coords, key=lambda c: c[2]*c[3])
            plate_img = img[y:y+h, x:x+w]
            
            # --- Enhanced OCR Preprocessing ---
            plate_gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
            
            # Adaptive thresholding works better than global for plates
            plate_thresh = cv2.adaptiveThreshold(
                plate_gray, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2)
            
            # Scale up for better OCR
            plate_thresh = cv2.resize(plate_thresh, None, fx=2, fy=2, 
                                    interpolation=cv2.INTER_CUBIC)
            
            # Additional denoising
            plate_thresh = cv2.medianBlur(plate_thresh, 3)
            
            # --- OCR Configuration ---
            custom_config = r'--oem 3 --psm 7 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            plate_text = pytesseract.image_to_string(plate_thresh, config=custom_config)
            plate_text = ''.join(e for e in plate_text if e.isalnum())
            
            if DEBUG_MODE:
                cv2.rectangle(img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                cv2.putText(img, plate_text, (x, y - 10), 
                           cv2.FONT_HERSHEY_SIMPLEX, 0.9, (0, 255, 0), 2)
                cv2.imshow('Processed', img)
                cv2.imshow('Plate Region', plate_thresh)
                cv2.waitKey(1)
            
            if SAVE_IMAGES:
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                os.makedirs("captures", exist_ok=True)
                cv2.imwrite(f"captures/{plate_text}_{timestamp}.jpg", img) if plate_text else None
            
            print(f"[DEBUG] Detected: {plate_text}" if plate_text else "[DEBUG] No text recognized")
            return plate_text if plate_text else None
            
        except Exception as e:
            print(f"[ERROR] Plate recognition failed: {str(e)}")
            return None