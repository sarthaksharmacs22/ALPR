
###       WORKING FINE 

import cv2
import numpy as np
import pytesseract
from datetime import datetime
import os
from config import PLATE_MIN_AREA, PLATE_RATIO, DEBUG_MODE, SAVE_IMAGES

class PlateRecognizer:
    def __init__(self):
        # Configure Tesseract path (try common locations)
        tess_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Tesseract-OCR\tesseract.exe"
        ]
        for path in tess_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                break
        else:
            raise FileNotFoundError("Tesseract not found. Install it and set the path")

        # Indian plate validation parameters
        self.MIN_PLATE_LENGTH = 6
        self.MAX_PLATE_LENGTH = 10
        self.INDIAN_STATE_CODES = [
            'AP','AR','AS','BR','CG','GA','GJ','HR','HP','JH','KA','KL',
            'MP','MH','MN','ML','MZ','NL','OD','PB','RJ','SK','TN','TS',
            'TR','UP','UK','WB','AN','CH','DN','DD','DL','LD','PY'
        ]

    def preprocess_image(self, img):
        """Enhanced image preprocessing pipeline"""
        # Convert to grayscale and enhance contrast
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        gray = clahe.apply(gray)
        
        # Noise reduction and edge detection
        blur = cv2.bilateralFilter(gray, 11, 75, 75)
        edged = cv2.Canny(blur, 30, 200)
        
        # Morphological closing to connect edges
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
        return cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)

    def find_plate_contours(self, edged_img, original_img):
        """Find potential license plate contours with geometric validation"""
        contours, _ = cv2.findContours(edged_img.copy(), cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        valid_contours = []
        
        for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:10]:  # Top 10 largest
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            
            # Look for quadrilateral contours
            if len(approx) == 4:
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / float(h)
                area = w * h
                
                # Geometric validation
                if (area > PLATE_MIN_AREA and 
                    2.5 < aspect_ratio < PLATE_RATIO):
                    valid_contours.append((x, y, w, h))
                    
                    if DEBUG_MODE:
                        cv2.drawContours(original_img, [approx], -1, (0, 255, 255), 2)
        
        return valid_contours if valid_contours else None

    def validate_plate_text(self, text):
        """Indian license plate specific validation"""
        text = ''.join(e for e in text if e.isalnum())
        
        # Length check
        if not (self.MIN_PLATE_LENGTH <= len(text) <= self.MAX_PLATE_LENGTH):
            return None
        
        # State code check (first 2 characters)
        if len(text) >= 2 and text[:2] not in self.INDIAN_STATE_CODES:
            return None
            
        return text

    def recognize_plate(self, img):
        """Complete plate recognition pipeline"""
        try:
            # Stage 1: Plate detection
            processed = self.preprocess_image(img)
            plate_coords = self.find_plate_contours(processed, img)
            
            if not plate_coords:
                if DEBUG_MODE:
                    print("[DEBUG] No valid plate contours found")
                return None
            
            # Get the most promising candidate
            x, y, w, h = max(plate_coords, key=lambda c: c[2]*c[3])
            plate_roi = img[y:y+h, x:x+w]
            
            # Stage 2: OCR preparation
            plate_gray = cv2.cvtColor(plate_roi, cv2.COLOR_BGR2GRAY)
            plate_thresh = cv2.adaptiveThreshold(
                plate_gray, 255,
                cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                cv2.THRESH_BINARY, 11, 2)
            
            # Enhance for OCR
            plate_thresh = cv2.resize(plate_thresh, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
            plate_thresh = cv2.medianBlur(plate_thresh, 3)
            
            # Stage 3: OCR
            custom_config = r'--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            plate_text = pytesseract.image_to_string(plate_thresh, config=custom_config)
            
            # Stage 4: Validation
            validated_text = self.validate_plate_text(plate_text)
            
            if DEBUG_MODE:
                debug_img = img.copy()
                cv2.rectangle(debug_img, (x, y), (x+w, y+h), (0, 255, 0), 2)
                status = f"Valid: {validated_text}" if validated_text else "Invalid"
                cv2.putText(debug_img, status, (x, y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                cv2.imshow('Debug', debug_img)
                cv2.imshow('Plate ROI', plate_thresh)
                cv2.waitKey(1)
            
            if SAVE_IMAGES and validated_text:
                os.makedirs("captures", exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                cv2.imwrite(f"captures/{validated_text}_{timestamp}.jpg", img)
            
            return validated_text
            
        except Exception as e:
            if DEBUG_MODE:
                print(f"[ERROR] Recognition failed: {str(e)}")
            return None