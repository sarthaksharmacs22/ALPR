"""""
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import SPREADSHEET_ID, WORKSHEET_NAME
import os
from config import ENTRY_POINT_NAME  # Add this line with other imports
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

class GoogleSheetsHandler:
    def __init__(self):
        scope = [
          'https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive.file',
          'https://www.googleapis.com/auth/drive'
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name(
            'platetrackerfullaccess-8e6fbccc7a40.json', scope)
        self.client = gspread.authorize(creds)
        self.sheet = self.client.open_by_key(SPREADSHEET_ID).worksheet(WORKSHEET_NAME)
        
        # Create headers if sheet is empty
        if not self.sheet.get_all_records():
            self.sheet.append_row([
                "License Plate", 
                "Entry Time", 
                "Exit Time", 
                "Duration (minutes)", 
                "Entry Point"
            ])

    def log_vehicle(self, plate, event_type):
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        records = self.sheet.get_all_records()
        
        # Check for existing entry without exit
        if event_type == "EXIT":
            for i, row in enumerate(records, start=2):  # start=2 because sheet is 1-indexed and first row is header
                if row["License Plate"] == plate and row["Exit Time"] == "":
                    self.sheet.update_cell(i, 3, now)  # Update Exit Time
                    entry_time = datetime.strptime(row["Entry Time"], "%Y-%m-%d %H:%M:%S")
                    exit_time = datetime.strptime(now, "%Y-%m-%d %H:%M:%S")
                    duration = (exit_time - entry_time).total_seconds() / 60
                    self.sheet.update_cell(i, 4, round(duration, 2))
                    return True
            return False
        else:  # ENTRY
            self.sheet.append_row([
                plate, 
                now, 
                "", 
                "", 
                ENTRY_POINT_NAME
            ])
            return True
"""""


"""""
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime

# Define Google Sheets scope and credentials file
SCOPE = ["https://spreadsheets.google.com/feeds",'https://www.googleapis.com/auth/spreadsheets', "https://www.googleapis.com/auth/drive"]
CREDS_FILE = "platetrackerfullaccess-8e6fbccc7a40.json"  # Make sure this file is in the same directory

class GoogleSheetHandler:
    def __init__(self, sheet_name="VehicleLogs"):
        creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, SCOPE)
        client = gspread.authorize(creds)
        self.sheet = client.open(sheet_name).sheet1

        # Ensure headers are in place
        headers = self.sheet.row_values(1)
        if not headers or headers != ["Time of Entry", "Time of Exit", "License Plate No.", "Duration (minutes)", "Entry Point"]:
            self.sheet.update("A1:E1", [["Time of Entry", "Time of Exit", "License Plate No.", "Duration (minutes)", "Entry Point"]])

        self.active_vehicles = {}  # Dict to track entry times

    def log_vehicle(self, plate_text, entry_point="Gate1"):
        now = datetime.now()
        current_time = now.strftime("%Y-%m-%d %H:%M:%S")

        if plate_text in self.active_vehicles:
            # Already present -> Exit case
            entry_time = self.active_vehicles.pop(plate_text)
            duration_minutes = int((now - entry_time).total_seconds() / 60)
            self.sheet.append_row([entry_time.strftime("%Y-%m-%d %H:%M:%S"), current_time, plate_text, str(duration_minutes), entry_point])
            print(f"🚗 Logged EXIT for plate: {plate_text} | Duration: {duration_minutes} mins")
            return "EXIT"

        else:
            # New entry
            self.active_vehicles[plate_text] = now
            self.sheet.append_row([current_time, "", plate_text, "", entry_point])
            print(f"🟢 Logged ENTRY for plate: {plate_text} at {current_time}")
            return "ENTRY"
"""





import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
from typing import Dict, Optional

# Constants
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
CREDS_FILE = "platetrackerfullaccess-8e6fbccc7a40.json"
DEFAULT_ENTRY_POINT = "Main Gate"

class GoogleSheetHandler:
    def __init__(self, sheet_name="VehicleLogs"):
        """Initialize Google Sheets handler with connection and header verification"""
        try:
            # Validate credentials file exists
            if not os.path.exists(CREDS_FILE):
                raise FileNotFoundError(f"Credentials file '{CREDS_FILE}' not found")
            
            # Authorize and connect to sheet
            creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, SCOPE)
            client = gspread.authorize(creds)
            self.sheet = client.open(sheet_name).sheet1
            
            # Define expected headers
            self.expected_headers = [
                "Time of Entry",
                "Time of Exit",
                "License Plate No.",
                "Duration (minutes)",
                "Entry Point"
            ]
            
            # Verify and update headers if needed
            self._verify_headers()
            
            # Initialize active vehicles cache
            self.active_vehicles = self._load_active_vehicles()
            
            print(f"✅ Connected to Google Sheet: '{sheet_name}'")
            
        except Exception as e:
            print(f"❌ Error initializing Google Sheet handler: {str(e)}")
            raise

    def _verify_headers(self):
        """Ensure sheet headers match expected format"""
        try:
            current_headers = self.sheet.row_values(1)
            
            # If headers don't match exactly, update them
            if current_headers != self.expected_headers:
                self.sheet.update('A1:E1', [self.expected_headers])
                print("✅ Updated sheet headers to standard format")
                
        except Exception as e:
            print(f"❌ Failed to verify/update sheet headers: {str(e)}")
            raise

    def _load_active_vehicles(self):
    ##"""Load vehicles with no exit time into memory for quick lookup"""
        active_map = {}
        try:
            records = self.sheet.get_all_records(expected_headers=self.expected_headers)
            
            for i, row in enumerate(records, start=2):  # Rows start at 2 (header is row 1)
                # Safely get and clean plate text
                plate = str(row.get("License Plate No.", "")).strip()
                
                # Safely check exit time (convert to string first)
                exit_time = str(row.get("Time of Exit", "")).strip()
                
                if plate and not exit_time:
                    active_map[plate] = {
                        'row_index': i,
                        'entry_time': str(row.get("Time of Entry", "")).strip()
                    }
                    
        except Exception as e:
            print(f"⚠️ Could not load active vehicles: {str(e)}")
            
        return active_map

    def _calculate_duration(self, entry_time_str: str, exit_time: datetime) -> float:
        """Calculate duration in minutes between entry and exit times"""
        try:
            entry_time = datetime.strptime(entry_time_str, "%Y-%m-%d %H:%M:%S")
            return round((exit_time - entry_time).total_seconds() / 60, 2)
        except ValueError:
            print(f"⚠️ Invalid entry time format: {entry_time_str}")
            return 0.0

    def _update_exit(self, plate: str, exit_time: datetime) -> bool:
    ##Update sheet with exit time while preserving license plate"""
        if plate not in self.active_vehicles:
            print(f"⚠️ Plate {plate} not found in active vehicles")
            return False

        vehicle = self.active_vehicles[plate]
        
        # Debug: Print entry_time and its type
        print(f"[DEBUG] Entry Time: {vehicle['entry_time']} (Type: {type(vehicle['entry_time'])})")
        
        # Ensure entry_time is a datetime object
        if isinstance(vehicle['entry_time'], str):
            try:
                entry_time = datetime.strptime(vehicle['entry_time'], "%Y-%m-%d %H:%M:%S")
            except ValueError as e:
                print(f"❌ Invalid entry_time format for {plate}: {e}")
                return False
        else:
            entry_time = vehicle['entry_time']
        
        duration = (exit_time - entry_time).total_seconds() / 60  # in minutes
        
        # Enforce minimum 1 minute duration
        if duration < 1:
            print(f"⏳ Plate {plate} parked for only {duration:.2f} mins (minimum 1 min required)")
            return False
        
        try:
            # Print debug info before updating
            print(f"[DEBUG] Updating row {vehicle['row_index']} with exit_time: {exit_time}, duration: {duration:.2f} mins")
            
            # Update Time of Exit (Column B) and Duration (Column D)
            self.sheet.batch_update([{
                'range': f"B{vehicle['row_index']}",
                'values': [[exit_time.strftime("%Y-%m-%d %H:%M:%S")]]
            }, {
                'range': f"D{vehicle['row_index']}",
                'values': [[f"{duration:.2f}"]]
            }])
            
            # Remove from active vehicles
            del self.active_vehicles[plate]
            print(f"🔴 EXIT: {plate} | Duration: {duration:.2f} mins")
            return True
            
        except Exception as e:
            print(f"❌ Failed to update exit for {plate}: {str(e)}")
        return False
    
    def _create_entry(self, plate: str, entry_time: datetime, entry_point: str) -> bool:
        """Create new vehicle entry in the sheet"""
        try:
            new_row = [
                entry_time.strftime("%Y-%m-%d %H:%M:%S"),  # Time of Entry
                "",  # Time of Exit
                plate,  # License Plate
                "",  # Duration
                entry_point  # Entry Point
            ]
            
            # Append new row and get its index
            self.sheet.append_row(new_row)
            new_index = len(self.sheet.get_all_records()) + 1
            
            # Update active vehicles cache
            self.active_vehicles[plate] = {
                'row_index': new_index,
                'entry_time': new_row[0]
            }
            
            print(f"🟢 ENTRY: {plate} at {new_row[0]}")
            return True
            
        except Exception as e:
            print(f"❌ Failed to create entry for {plate}: {str(e)}")
            return False

    def log_to_sheet(self, plate_text: str, entry_point: str = None) -> bool:
        """
        Log vehicle entry or exit to Google Sheet.
        
        Args:
            plate_text: License plate number
            entry_point: Entry point name (uses default if None)
            
        Returns:
            True if operation succeeded, False otherwise
        """
        if not plate_text or not plate_text.strip():
            print("⚠️ Empty or invalid plate text provided")
            return False

        plate_text = plate_text.strip().upper()
        entry_point = entry_point or DEFAULT_ENTRY_POINT
        current_time = datetime.now()

        try:
            # First verify headers are correct
            self._verify_headers()
            
            if plate_text in self.active_vehicles:
                return self._update_exit(plate_text, current_time)
            else:
                return self._create_entry(plate_text, current_time, entry_point)
                
        except Exception as e:
            print(f"❌ Unexpected error logging {plate_text}: {str(e)}")
            return False