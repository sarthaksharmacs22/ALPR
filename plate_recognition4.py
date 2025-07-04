import cv2
import numpy as np
import pytesseract
from datetime import datetime
import os
from google_sheets import GoogleSheetHandler
from config import DEBUG_MODE, SAVE_IMAGES

class PlateRecognizer:
    def __init__(self):
        # Tesseract OCR configuration
        tess_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Tesseract-OCR\tesseract.exe",
            os.path.expandvars(r"%LOCALAPPDATA%\Tesseract-OCR\tesseract.exe")
        ]
        
        for path in tess_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                break
        else:
            raise FileNotFoundError(
                "Tesseract OCR not found. Please install from:\n"
                "https://github.com/UB-Mannheim/tesseract/wiki"
            )
        
        # Initialize Google Sheets handler
        self.sheets_handler = GoogleSheetHandler()
        
        # Indian plate configuration
        self.INDIAN_STATE_CODES = ['RJ','DL','MH','KA','TN','AP','UP','WB','GJ','MP']
        self.CHAR_CORRECTIONS = {
            'A': '4', 'B': '8', 'D': '0', 'G': '6',
            'I': '1', 'O': '0', 'Q': '0', 'S': '5',
            'T': '7', 'Z': '2', '4': 'A', '7': 'T'
        }
        self.MIN_PLATE_AREA = 2000  # Minimum area for plate contour
        self.MAX_PLATE_AREA = 10000  # Maximum area for plate contour

    def preprocess_image(self, img):
        """Enhanced preprocessing pipeline"""
        # Convert to grayscale and enhance contrast
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        
        # Noise reduction and edge detection
        blur = cv2.bilateralFilter(enhanced, 11, 75, 75)
        edged = cv2.Canny(blur, 30, 200)
        
        # Morphological closing
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
        return cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)

    def find_plate_contours(self, img):
        """Find potential license plate contours"""
        processed = self.preprocess_image(img)
        contours, _ = cv2.findContours(processed, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        plate_contours = []
        for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:10]:
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            
            if len(approx) == 4:  # Only quadrilateral contours
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / float(h)
                area = w * h
                
                # Validate based on Indian plate characteristics
                if (self.MIN_PLATE_AREA < area < self.MAX_PLATE_AREA and 
                    3.0 < aspect_ratio < 5.0):
                    plate_contours.append((x, y, w, h))
                    
                    if DEBUG_MODE:
                        cv2.drawContours(img, [approx], -1, (0,255,0), 2)
        
        return plate_contours

    def preprocess_for_ocr(self, plate_img):
        """Optimized preprocessing for Indian plate OCR"""
        gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
        
        # Adaptive thresholding
        thresh = cv2.adaptiveThreshold(
            gray, 255,
            cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
            cv2.THRESH_BINARY, 11, 2
        )
        
        # Scale up for better OCR
        scaled = cv2.resize(thresh, None, fx=2, fy=2, interpolation=cv2.INTER_CUBIC)
        
        # Denoising
        return cv2.medianBlur(scaled, 3)

    def clean_plate_text(self, text):
        """Correct common OCR mistakes for Indian plates"""
        corrected = []
        for c in text.upper():
            if c in self.CHAR_CORRECTIONS:
                corrected.append(self.CHAR_CORRECTIONS[c])
            elif c.isalnum():
                corrected.append(c)
        return ''.join(corrected)

    def validate_plate(self, text):
        """Strict validation for Indian plate format"""
        if not text or len(text) < 8:
            return None
            
        clean_text = self.clean_plate_text(text)
        
        # Validate state code
        if len(clean_text) >= 2 and clean_text[:2] not in self.INDIAN_STATE_CODES:
            return None
            
        # Validate digit positions (last 4 characters should contain digits)
        if len(clean_text) >= 4 and sum(c.isdigit() for c in clean_text[-4:]) < 2:
            return None
            
        return clean_text

    def recognize_and_log_plate(self, img, location="Main Gate"):
        """Complete recognition and logging pipeline"""
        try:
            # Step 1: Detect potential plates
            plate_contours = self.find_plate_contours(img)
            if not plate_contours:
                if DEBUG_MODE:
                    cv2.imshow('Debug', img)
                    cv2.waitKey(1)
                return None
            
            # Step 2: Process the most likely plate
            x, y, w, h = max(plate_contours, key=lambda c: c[2]*c[3])
            plate_roi = img[y:y+h, x:x+w]
            
            # Step 3: Enhanced OCR preprocessing
            plate_thresh = self.preprocess_for_ocr(plate_roi)
            
            # Step 4: OCR with Indian plate optimizations
            custom_config = r'--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHJKLMNPRSTUVWXYZ0123456789'
            raw_text = pytesseract.image_to_string(plate_thresh, config=custom_config)
            plate_text = self.validate_plate(raw_text)
            
            # Step 5: Visualization and logging
            if DEBUG_MODE:
                debug_img = img.copy()
                cv2.rectangle(debug_img, (x,y), (x+w,y+h), (0,255,0), 2)
                if plate_text:
                    cv2.putText(debug_img, plate_text, (x,y-10), 
                               cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
                cv2.imshow('Debug', debug_img)
                cv2.waitKey(1)
            
            # Step 6: Log to Google Sheets
            if plate_text:
                entry_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.sheets_handler.log_vehicle(
                    plate=plate_text,
                    entry_time=entry_time,
                    location=location
                )
                
                if SAVE_IMAGES:
                    os.makedirs("captures", exist_ok=True)
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    cv2.imwrite(f"captures/{plate_text}_{timestamp}.jpg", img)
            
            return plate_text
            
        except Exception as e:
            if DEBUG_MODE:
                print(f"[ERROR] {str(e)}")
            return None