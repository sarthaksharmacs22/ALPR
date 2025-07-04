import cv2
import numpy as np
import pytesseract
from datetime import datetime
import os
import re
from config import PLATE, APP

# Then access the values as:
PLATE_MIN_AREA = PLATE['MIN_AREA']
PLATE_RATIO = PLATE['MAX_RATIO']  # or whichever ratio you need
DEBUG_MODE = APP['DEBUG_MODE']
SAVE_IMAGES = APP['SAVE_IMAGES']

class PlateRecognizer:
    def __init__(self, gsheet_handler_instance, debug_mode=False, save_images=False):
        # Initialize Tesseract paths
        self._initialize_tesseract()
        
        # Indian state codes for validation
        self.INDIAN_STATE_CODES = ['RJ', 'DL', 'MH', 'KA', 'TN', 'AP', 'UP', 'WB', 
                                  'GJ', 'MP', 'HR', 'PB', 'TS', 'GA', 'KL', 'CH', 
                                  'BR', 'CG', 'JH', 'UK', 'HP', 'OR', 'AS', 'AR', 
                                  'MZ', 'MN', 'NL', 'TR', 'SK', 'LD', 'AN', 'PY', 
                                  'LA', 'JK']

        # Character correction mapping (letters to numbers only)
        self.CHAR_CORRECTIONS = {
            'O': '0', 'Q': '0',  # Letters that look like 0
            'I': '1', 'L': '1',  # Letters that look like 1
            'S': '5',            # S often mistaken for 5
            'G': '6',            # G often mistaken for 6
            'Z': '2',            # Z often mistaken for 2
            'B': '8',            # B often mistaken for 8
            'T': '7',            # T often mistaken for 7
            'A': '4',            # A often mistaken for 4
            'M':'H'
        }

        # Plate regex patterns
        self.STANDARD_PLATE_REGEX = re.compile(r"^[A-Z]{2}[0-9]{1,2}[A-Z]{1,2}[0-9]{4}$")
        self.BH_PLATE_REGEX = re.compile(r"^[0-9]{2}BH[0-9]{1,2}[A-Z]{1,2}[0-9]{4}$")

        # Store configuration
        self.gsheet_handler = gsheet_handler_instance
        self.DEBUG_MODE = debug_mode
        self.SAVE_IMAGES = save_images
        self.ocr_window_created = False

    def _initialize_tesseract(self):
        """Initialize Tesseract OCR paths"""
        tess_paths = [
            r"C:\Program Files\Tesseract-OCR\tesseract.exe",
            r"C:\Tesseract-OCR\tesseract.exe",
            r"C:\Users\{}\AppData\Local\Tesseract-OCR\tesseract.exe".format(os.getenv('USERNAME'))
        ]
        
        for path in tess_paths:
            if os.path.exists(path):
                pytesseract.pytesseract.tesseract_cmd = path
                return
        raise FileNotFoundError("Tesseract OCR not found in any standard locations.")

    def preprocess_for_detection(self, img):
        """Preprocess image for plate detection"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        blur = cv2.bilateralFilter(gray, 11, 75, 75)
        
        # Automatic Canny edge detection
        v = np.median(blur)
        lower = int(max(0, (1.0 - 0.33) * v))
        upper = int(min(255, (1.0 + 0.33) * v))
        edged = cv2.Canny(blur, lower, upper)
        
        # Morphological closing
        kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3,3))
        return cv2.morphologyEx(edged, cv2.MORPH_CLOSE, kernel)

    def preprocess_for_ocr(self, plate_img):
        """Enhance plate image for better OCR results"""
        gray = cv2.cvtColor(plate_img, cv2.COLOR_BGR2GRAY)
        
        # Contrast Limited Adaptive Histogram Equalization
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced = clahe.apply(gray)
        
        # Adaptive thresholding
        thresh = cv2.adaptiveThreshold(enhanced, 255,
                                      cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                      cv2.THRESH_BINARY, 11, 4)
        
        # Morphological operations
        kernel_erode = np.ones((1,1), np.uint8)
        kernel_dilate = np.ones((2,2), np.uint8)
        cleaned = cv2.morphologyEx(thresh, cv2.MORPH_OPEN, kernel_erode)
        cleaned = cv2.dilate(cleaned, kernel_dilate, iterations=1)
        
        # Sharpening
        blurred = cv2.GaussianBlur(cleaned, (0,0), 3)
        sharpened = cv2.addWeighted(cleaned, 1.5, blurred, -0.5, 0)
        
        # Upscale for better OCR
        return cv2.resize(sharpened, None, fx=2.5, fy=2.5, 
                         interpolation=cv2.INTER_CUBIC)

    def detect_plates(self, img):
        """Detect potential license plates in image"""
        processed = self.preprocess_for_detection(img)
        contours, _ = cv2.findContours(processed, cv2.RETR_TREE, 
                                      cv2.CHAIN_APPROX_SIMPLE)
        
        plate_contours = []
        for contour in sorted(contours, key=cv2.contourArea, reverse=True)[:10]:
            peri = cv2.arcLength(contour, True)
            approx = cv2.approxPolyDP(contour, 0.02 * peri, True)
            
            if len(approx) == 4:  # Only quadrilateral contours
                x, y, w, h = cv2.boundingRect(contour)
                aspect_ratio = w / float(h)
                
                # Plate-like aspect ratio and minimum size
                if 2.5 < aspect_ratio < 6.0 and h > 20 and w > 80:
                    plate_contours.append((x, y, w, h))
                    
                    if self.DEBUG_MODE:
                        cv2.drawContours(img, [approx], -1, (0,255,255), 2)
                        
        return plate_contours

    def clean_plate_text(self, text):
        """Clean and correct OCR output"""
        # Remove non-alphanumeric characters except spaces and hyphens
        temp_text = re.sub(r'[^A-Z0-9 -]', '', text.upper())
        corrected = ''
    
         
        for i, char in enumerate(temp_text):
        # First 2 chars (state code): keep alphabets
            if i < 2:
                corrected += char
            # Next 2: numbers (region code)
            elif 2 <= i < 4:
                corrected += self.CHAR_CORRECTIONS.get(char, char)
            # Next 1–2: series (alphabets)
            elif 4 <= i < 6:
                corrected += char
            # Last 4: numbers
            else:
                corrected += self.CHAR_CORRECTIONS.get(char, char)

        return corrected
        
        

    def validate_indian_plate(self, text):
        """Validate if text matches Indian plate formats"""
        if not text:
            return None
            
        corrected_text = self.clean_plate_text(text)
        
        # Standard format (e.g., MH01AB1234)
        if (self.STANDARD_PLATE_REGEX.match(corrected_text) and 
            corrected_text[:2] in self.INDIAN_STATE_CODES):
            return corrected_text
            
        # BH series format (e.g., 12BH2345A)
        if self.BH_PLATE_REGEX.match(corrected_text):
            return corrected_text
            
        return None

    def recognize_plate(self, img):
        """Main method to detect and recognize license plates"""
        try:
            plate_contours = self.detect_plates(img)
            
            if not plate_contours:
                self._show_debug_output(img, "No plate detected")
                return None
                
            # Get largest contour
            x, y, w, h = max(plate_contours, key=lambda c: c[2]*c[3])
            plate_roi = img[y:y+h, x:x+w]
            
            # OCR processing
            plate_thresh = self.preprocess_for_ocr(plate_roi)
            config = r'--oem 3 --psm 8 -c tessedit_char_whitelist=ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789'
            raw_text = pytesseract.image_to_string(plate_thresh, config=config)
            
            # Validate plate format
            plate_text = self.validate_indian_plate(raw_text)
            
            # Debug output
            if self.DEBUG_MODE:
                self._show_debug_output(img, plate_text or raw_text.strip(), 
                                       (x, y, w, h), plate_thresh)
            
            # Save image if valid plate found
            if plate_text and self.SAVE_IMAGES:
                self._save_plate_image(img, plate_text)
                
            # Log to Google Sheets
            if plate_text:
                self.gsheet_handler.log_to_sheet(plate_text)
                
            return plate_text
            
        except Exception as e:
            if self.DEBUG_MODE:
                print(f"[ERROR] Plate recognition failed: {str(e)}")
            return None

    def _show_debug_output(self, img, text, bbox=None, plate_img=None):
        """Helper method for debug visualization"""
        debug_img = img.copy()
        
        if bbox:
            x, y, w, h = bbox
            cv2.rectangle(debug_img, (x,y), (x+w,y+h), (0,255,0), 2)
            status = f"Valid: {text}" if self.validate_indian_plate(text) else f"Invalid: {text}"
            cv2.putText(debug_img, status, (x,y-10), cv2.FONT_HERSHEY_SIMPLEX, 
                       0.7, (0,255,0) if status.startswith('Valid') else (0,0,255), 2)
        
        cv2.imshow('Detection', debug_img)
        
        if plate_img is not None:
            cv2.imshow('OCR Input', plate_img)
            self.ocr_window_created = True
        elif self.ocr_window_created:
            cv2.destroyWindow('OCR Input')
            self.ocr_window_created = False
            
        cv2.waitKey(1)

    def _save_plate_image(self, img, plate_text):
        """Helper method to save plate images"""
        os.makedirs("captures", exist_ok=True)
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"captures/{''.join(filter(str.isalnum, plate_text))}_{timestamp}.jpg"
        cv2.imwrite(filename, img)
        
