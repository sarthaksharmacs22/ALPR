import cv2
import time
import os
from datetime import datetime # Already imported by other modules, but good to keep if used directly
import re # Add re import if PlateRecognizer uses it and is defined inline

# Import your modules
from plate_recognition5 import PlateRecognizer
from google_sheets import GoogleSheetHandler

# Assuming config.py exists and defines these
from config import CAMERA_SOURCE, DEBUG_MODE, SAVE_IMAGES # Renamed SAVE_IMAGES to avoid conflict

def main():
    # Create captures folder if it doesn't exist
    if not os.path.exists('captures'):
        os.makedirs('captures')

    # Initialize Google Sheets handler first
    # This also handles the credentials file check
    try:
        sheets_handler = GoogleSheetHandler(sheet_name="VehicleLogs")
    except Exception as e:
        print(f"❌ Error: Could not initialize Google Sheet handler. Please check credentials and network. {e}")
        return # Exit if sheets cannot be initialized

    # Initialize PlateRecognizer, passing the sheets_handler instance
    # Also pass DEBUG_MODE and SAVE_IMAGES_GLOBAL from config
    recognizer = PlateRecognizer(
        gsheet_handler_instance=sheets_handler,
        debug_mode=DEBUG_MODE, # Pass DEBUG_MODE from config
        save_images=SAVE_IMAGES # Pass SAVE_IMAGES from config
    )

    # Initialize video capture
    cap = cv2.VideoCapture(CAMERA_SOURCE)
    if not cap.isOpened():
        print(f"❌ Failed to open camera (Source: {CAMERA_SOURCE}). Check your CAMERA_SOURCE in config.py or camera connection.")
        return

    # Removed recent_plates; logic will be handled by GoogleSheetHandler
    # print statements from sheets_handler.log_to_sheet will indicate entry/exit

    print("✅ License Plate Recognition System Started... Press Ctrl+C or 'q' to exit.")

    try:
        while True:
            ret, frame = cap.read()
            if not ret or frame is None:
                print("❌ Failed to read frame from camera. Reconnecting or ending stream.")
                # Optional: Add re-connection logic here if camera drops frames
                time.sleep(2) # Wait a bit before trying again
                continue # Skip to next iteration

            # Recognize plate; it will internally call the sheets_handler
            # The recognize_plate method returns the validated plate_text or None
            plate_text = recognizer.recognize_plate(frame)

            # The logging to sheet happens inside PlateRecognizer.recognize_plate
            # We just need to ensure the print statements are informative in main
            if plate_text:
                # No need for recent_plates logic here, it's handled by GoogleSheetHandler
                # sheets_handler.log_to_sheet will print "🟢 ENTRY" or "🔴 EXIT" messages
                pass # The logging call is already inside recognizer.recognize_plate

            if DEBUG_MODE: # Use DEBUG_MODE from config
                cv2.imshow("📷 Live Feed", frame)
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    print("🛑 Exiting by user command.")
                    break

            # Add a small delay to avoid consuming 100% CPU on fast systems
            # Adjust as needed, e.g., 0.1 for ~10 FPS, 1 for ~1 FPS
            time.sleep(0.1) 

    except KeyboardInterrupt:
        print("\n🛑 Exiting by keyboard interrupt.")
    except Exception as e:
        print(f"❌ Unexpected error in main loop: {str(e)}")
    finally:
        cap.release()
        cv2.destroyAllWindows()
        print("🛑 System stopped.")

if __name__ == "__main__":
    main()