import cv2
import numpy as np
import pytesseract
from datetime import datetime
import os
from config import DEBUG_MODE, SAVE_IMAGES

class PlateRecognizer:
    def __init__(self):
        # Configure Tesseract paths
        tess_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Tesseract-OCR\tesseract.exe",
            r"C:\Users\{}\AppData\Local\Tesseract-OCR\tesseract.exe".format(os.getenv('USERNAME'))
        ]
        
        for path in tess_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                break
        else:
            raise FileNotFoundError("Tesseract OCR not found. Please install it from https://github.com/UB-Mannheim/tesseract/wiki")

        # Indian plate configuration
        self.INDIAN_STATE_CODES = ['RJ','DL','MH','KA','TN','AP','UP','WB','GJ','MP']
        self.MIN_PLATE_LENGTH = 8
        self.MAX_PLATE_LENGTH = 10
        
        # Character correction mapping (specific to Indian plates)
        self.CHAR_CORRECTIONS = {
            'A': '4', 'B': '8', 'D': '0', 'G': '6',
            'I': '1', 'O': '0', 'Q': '0', 'S': '5',
            'T': '7', 'Z': '2', '4': 'A', '7': 'T'
        }

    def preprocess_for_detection(self, img):
        """Enhanced preprocessing for plate detection"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.bilateralFilter(gray, 11, 75, 75)
        
        # Dynamic Canny thresholds
        v = np.median(blur)
        lower = int(max(0, (1.0 - 0.33) * v))
        upper = int(min(255, (1.0 + 0.33) * v))
        edged = cv2.Canny(blur, lower, upper)
        
        # Morphological operations
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
        return cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)

    def preprocess_for_ocr(self, plate_img):
        """Specialized preprocessing for Indian plates"""
        gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
        
        # CLAHE contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=3.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        
        # Adaptive thresholding
        thresh = cv2.adaptiveThreshold(enhanced, 255,
                                     cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                     cv2.THRESH_BINARY, 11, 4)
        
        # Noise removal
        kernel = np.ones((2,2), np.uint8)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel)
        
        # Scale up for better OCR
        return cv2.resize(cleaned, None, fx=1.5, fy=1.5, interpolation=cv2.INTER_CUBIC)

    def detect_plates(self, img):
        """Find potential license plate regions"""
        processed = self.preprocess_for_detection(img)
        contours, _ = cv2.findContours(processed, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        plate_contours = []
        for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:10]:
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            
            if len(approx) == 4:  # Look for quadrilaterals
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / float(h)
                
                # Indian plates typically have aspect ratio between 3.5 and 5.0
                if 3.5 < aspect_ratio < 5.0:
                    plate_contours.append((x, y, w, h))
                    
                    if DEBUG_MODE:
                        cv2.drawContours(img, [approx], -1, (0,255,255), 2)
        
        return plate_contours

    def clean_plate_text(self, text):
        """Correct common OCR mistakes for Indian plates"""
        cleaned = []
        for c in text:
            uc = c.upper()
            if uc in self.CHAR_CORRECTIONS:
                cleaned.append(self.CHAR_CORRECTIONS[uc])
            elif uc.isalnum():
                cleaned.append(uc)
        return ''.join(cleaned)

    def validate_indian_plate(self, text):
        """Strict validation for Indian plate format"""
        if not text or len(text) < self.MIN_PLATE_LENGTH:
            return None
            
        clean_text = self.clean_plate_text(text)
        
        # Check state code
        if len(clean_text) >= 2 and clean_text[:2] not in self.INDIAN_STATE_CODES:
            return None
            
        # Check for at least 4 ending digits (Indian plate standard)
        if len(clean_text) >= 4 and sum(c.isdigit() for c in clean_text[-4:]) < 3:
            return None
            
        return clean_text

    def recognize_plate(self, img):
        """Complete recognition pipeline"""
        try:
            # Stage 1: Plate detection
            plate_contours = self.detect_plates(img)
            if not plate_contours:
                if DEBUG_MODE:
                    cv2.imshow('Detection', img)
                    cv2.waitKey(1)
                return None
            
            # Take the most prominent plate candidate
            x, y, w, h = max(plate_contours, key=lambda c: c[2]*c[3])
            plate_roi = img[y:y+h, x:x+w]
            
            # Stage 2: OCR preprocessing
            plate_thresh = self.preprocess_for_ocr(plate_roi)
            
            # Stage 3: OCR with Indian plate optimizations
            custom_config = r'--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHJKLMNPRSTUVWXYZ0123456789'
            raw_text = pytesseract.image_to_string(plate_thresh, config=custom_config)
            
            # Stage 4: Text cleaning and validation
            plate_text = self.validate_indian_plate(raw_text)
            
            # Debug visualization
            if DEBUG_MODE:
                debug_img = img.copy()
                cv2.rectangle(debug_img, (x,y), (x+w,y+h), (0,255,0), 2)
                status = f"{plate_text}" if plate_text else "No valid plate"
                cv2.putText(debug_img, status, (x,y-10), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,255,0), 2)
                
                cv2.imshow('Detection', debug_img)
                cv2.imshow('OCR Input', plate_thresh)
                cv2.waitKey(1)
            
            # Save valid detections
            if plate_text and SAVE_IMAGES:
                os.makedirs("captures", exist_ok=True)
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                cv2.imwrite(f"captures/{plate_text}_{timestamp}.jpg", img)
            
            return plate_text
            
        except Exception as e:
            if DEBUG_MODE:
                print(f"[ERROR] {str(e)}")
            return None