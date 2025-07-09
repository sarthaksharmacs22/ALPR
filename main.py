"""""
import cv2
import time
from plate_recognition import PlateRecognizer
from google_sheets import GoogleSheetsHandler
from config import CAMERA_SOURCE, DEBUG_MODE
import os

def main():
    # Create captures directory if it doesn't exist
    if not os.path.exists('captures'):
        os.makedirs('captures')
    
    # Initialize components
    recognizer = PlateRecognizer()
    sheets_handler = GoogleSheetsHandler()
    cap = cv2.VideoCapture(CAMERA_SOURCE)
    
    # Dictionary to track recently seen plates (avoid duplicate logging)
    recent_plates = {}
    
    print("License Plate Recognition System Started...")
    
    
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret:
                print("Error reading from camera")
                break
            
            plate_text = recognizer.recognize_plate(frame)
            
            if plate_text:
                current_time = time.time()
                
                # Check if we've seen this plate recently (within 2 minutes)
                if plate_text in recent_plates:
                    if current_time - recent_plates[plate_text] > 120:  # 2 minutes
                        # Log as exit if it's been more than 2 minutes
                        if sheets_handler.log_vehicle(plate_text, "EXIT"):
                            print(f"Logged EXIT for plate: {plate_text}")
                            del recent_plates[plate_text]
                else:
                    # Log as new entry
                    if sheets_handler.log_vehicle(plate_text, "ENTRY"):
                        print(f"Logged ENTRY for plate: {plate_text}")
                        recent_plates[plate_text] = current_time
            
            if DEBUG_MODE:
                cv2.imshow('Camera Feed', frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
                    
            time.sleep(1)  # Process every second
    
    except KeyboardInterrupt:
        print("Shutting down...")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
"""""


"""""
import cv2
import time
from plate_recognition import PlateRecognizer
from google_sheets import GoogleSheetHandler
from config import CAMERA_SOURCE, DEBUG_MODE
import os

def main():
    # Create captures directory if it doesn't exist
    if not os.path.exists('captures'):
        os.makedirs('captures')
    
    # Initialize components
    recognizer = PlateRecognizer()
    sheets_handler = GoogleSheetHandler()
    cap = cv2.VideoCapture(CAMERA_SOURCE)

    # Check if camera opened successfully
    if not cap.isOpened():
        print("❌ Unable to open camera. Check CAMERA_SOURCE in config.")
        return
    
    # Dictionary to track recently seen plates (avoid duplicate logging)
    recent_plates = {}
    
    print("✅ License Plate Recognition System Started... Press Ctrl+C or 'q' to exit.")
    
    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                print("⚠️ Failed to read frame from camera. Retrying...")
                time.sleep(1)
                continue  # Skip this iteration
            
            plate_text = recognizer.recognize_plate(frame)
            
            if plate_text:
                current_time = time.time()
                
                # Check if we've seen this plate recently (within 2 minutes)
                if plate_text in recent_plates:
                    if current_time - recent_plates[plate_text] > 120:  # 2 minutes
                        if sheets_handler.log_vehicle(plate_text, "EXIT"):
                            print(f"🟡 Logged EXIT for plate: {plate_text}")
                            del recent_plates[plate_text]
                else:
                    # Log as new entry
                    if sheets_handler.log_vehicle(plate_text, "ENTRY"):
                        print(f"🟢 Logged ENTRY for plate: {plate_text}")
                        recent_plates[plate_text] = current_time
            
            if DEBUG_MODE:
                cv2.imshow('Camera Feed', frame)
                
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("🛑 Exiting by user command.")
                    break
                    
            time.sleep(1)  # Process every second
    
    except KeyboardInterrupt:
        print("🛑 Shutting down due to keyboard interrupt...")
    
    finally:
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()
"""

import cv2
import time
import os
from datetime import datetime
from plate_recognition6 import PlateRecognizer
from google_sheets2 import GoogleSheetHandler
from config import CAMERA, APP

def main():
    # Create captures folder if it doesn't exist
    if not os.path.exists('captures'):
        os.makedirs('captures')

    # Initialize components
    sheets_handler = GoogleSheetHandler()
    recognizer = PlateRecognizer(
        gsheet_handler_instance=sheets_handler,
        debug_mode=APP['DEBUG_MODE'],
        save_images=APP['SAVE_IMAGES']
    )
    
    # Attempt to open camera
    cap = cv2.VideoCapture(CAMERA['SOURCE'])
    cap.set(cv2.CAP_PROP_FRAME_WIDTH, CAMERA['RESOLUTION'][0])
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, CAMERA['RESOLUTION'][1])
    
    if CAMERA['FOCUS'] > 0:
        cap.set(cv2.CAP_PROP_AUTOFOCUS, 0)  # Disable autofocus
        cap.set(cv2.CAP_PROP_FOCUS, CAMERA['FOCUS'])
    
    if not cap.isOpened():
        print("❌ Failed to open camera. Check your CAMERA_SOURCE in config.py.")
        return

    recent_plates = {}  # {plate_text: timestamp}
    print("✅ License Plate Recognition System Started... Press Ctrl+C or 'q' to exit.")

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                print("❌ Failed to read frame from camera.")
                time.sleep(1)  # Wait before retrying
                continue

            plate_text = recognizer.recognize_plate(frame)

            if plate_text:
                print(f"[🔍 DEBUG] Detected Plate Text: {plate_text}")
                current_time = time.time()

                # Avoid duplicate logging within 2 minutes
                if plate_text in recent_plates:
                    if current_time - recent_plates[plate_text] > 120:
                        status = sheets_handler.log_to_sheet(plate_text)
                        recent_plates[plate_text] = current_time
                        print(f"[📝 LOGGED] {plate_text} at {datetime.fromtimestamp(current_time)}")
                else:
                    status = sheets_handler.log_to_sheet(plate_text)
                    recent_plates[plate_text] = current_time
                    print(f"[📝 LOGGED] {plate_text} at {datetime.fromtimestamp(current_time)}")

            if APP['DEBUG_MODE']:
                cv2.imshow("📷 Live Feed", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("🛑 Exiting by user command.")
                    break

            time.sleep(1)  # ~1 FPS to reduce CPU load

    except KeyboardInterrupt:
        print("\n🛑 Exiting by keyboard interrupt.")
    except Exception as e:
        print(f"❌ Unexpected error: {str(e)}")
    finally:
        cap.release()
        cv2.destroyAllWindows()

if __name__ == "__main__":
    main()