import gspread
from oauth2client.service_account import ServiceAccountCredentials
from datetime import datetime
import os
import traceback
import time # <--- ADD THIS IMPORT
from typing import Dict, Optional
from openpyxl.utils import get_column_letter
from gspread.exceptions import APIError, SpreadsheetNotFound, WorksheetNotFound # <--- ADD THESE IMPORTS

# Constants
SCOPE = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
CREDS_FILE = "platetrackerfullaccess-2503a6ec83d7.json"
DEFAULT_ENTRY_POINT = "Main Gate"

class GoogleSheetHandler:
    def __init__(self, sheet_name="VehicleLogs"):
        """Initialize Google Sheets handler with connection and header verification"""
        self.sheet_name = sheet_name
        self.sheet = None # Initialize sheet to None
        self.expected_headers = [
            "Time of Entry",
            "Time of Exit",
            "License Plate No.",
            "Duration (minutes)",
            "Entry Point"
        ]
        self.active_vehicles = {} # Initialize active_vehicles here

        # Attempt to connect to the sheet during initialization with retry logic
        self._connect_to_sheet()
        
        # If connection was successful, load active vehicles
        if self.sheet:
            self.active_vehicles = self._load_active_vehicles()
            print(f"✅ Connected to Google Sheet: '{sheet_name}'")
        else:
            print(f"❌ Failed to connect to Google Sheet: '{sheet_name}'. Logging functionality will be limited.")


    def _connect_to_sheet(self, retries=5, delay=2):
        """Connects to Google Sheet with retry logic for API errors."""
        for i in range(retries):
            try:
                # Validate credentials file exists
                if not os.path.exists(CREDS_FILE):
                    raise FileNotFoundError(f"Credentials file '{CREDS_FILE}' not found")
                
                # Authorize and connect to sheet
                creds = ServiceAccountCredentials.from_json_keyfile_name(CREDS_FILE, SCOPE)
                client = gspread.authorize(creds)
                self.sheet = client.open(self.sheet_name).sheet1
                
                # Verify and update headers if needed (only if connection is successful)
                self._verify_headers()
                return # Connection successful, exit loop

            except FileNotFoundError as e:
                print(f"❌ Critical Error: {e}")
                self.sheet = None # Ensure sheet is None if file not found
                break # No point retrying if file not found
            except (APIError, SpreadsheetNotFound, WorksheetNotFound) as e: # Catch specific gspread exceptions
                if hasattr(e, 'response') and e.response.status_code == 503:
                    print(f"❌ Error connecting to Google Sheet (503): The service is currently unavailable. Retrying in {delay} seconds... (Attempt {i+1}/{retries})")
                    time.sleep(delay)
                    delay *= 2 # Exponential backoff
                elif isinstance(e, SpreadsheetNotFound):
                    print(f"❌ Error: Google Sheet '{self.sheet_name}' not found. Please check the name or permissions.")
                    self.sheet = None
                    break # No point retrying if sheet isn't found
                elif isinstance(e, WorksheetNotFound):
                    print(f"❌ Error: Worksheet 'Sheet1' not found in '{self.sheet_name}'. Please ensure it exists.")
                    self.sheet = None
                    break
                else: # Other API errors or GSpread exceptions
                    print(f"❌ Error connecting to Google Sheet: {e}")
                    import traceback # For detailed error
                    traceback.print_exc()
                    self.sheet = None
                    break # Break on other errors, might not be transient
            except Exception as e:
                print(f"❌ An unexpected error occurred during Google Sheet connection: {e}")
                import traceback
                traceback.print_exc()
                self.sheet = None
                break # Break for unknown errors
        
        # If loop finishes without successful connection, self.sheet will remain None

    def _verify_headers(self):
        """Ensure sheet headers match expected format"""
        if not self.sheet: # <--- ADD THIS CHECK
            print("⚠️ Sheet not connected, cannot verify headers.")
            return

        try:
            current_headers = self.sheet.row_values(1)
            
            # If headers don't match exactly, update them
            if current_headers != self.expected_headers:
                # Clear existing content if headers are wrong to avoid issues
                # self.sheet.clear() # <--- OPTIONAL: Uncomment if you want to clear sheet if headers are wrong
                self.sheet.update('A1:E1', [self.expected_headers])
                print("✅ Updated sheet headers to standard format")
            else:
                print("✅ Sheet headers are correct.") # <--- ADDED for clarity
                
        except APIError as e: # <--- Catch APIError specifically
            print(f"❌ API Error verifying/updating headers (Status: {e.response.status_code}): {e}")
            raise # Re-raise to be caught by _connect_to_sheet's outer try-except
        except Exception as e:
            print(f"❌ Failed to verify/update sheet headers: {str(e)}")
            raise

    def _load_active_vehicles(self):
        """Load vehicles with no exit time into memory for quick lookup"""
        if not self.sheet: # <--- ADD THIS CHECK
            print("⚠️ Sheet not connected, cannot load active vehicles.")
            return {} # Return empty dict if not connected

        active_map = {}
        print("Loading active vehicles from Google Sheet...") # <--- ADDED for clarity
        try:
            # Added retry logic for get_all_records
            retries = 3
            delay = 1
            for i in range(retries):
                try:
                    records = self.sheet.get_all_records(expected_headers=self.expected_headers)
                    break # Success, break out of retry loop
                except APIError as e:
                    if e.response.status_code == 503:
                        print(f"❌ API Error [503] loading active vehicles. Retrying in {delay}s (Attempt {i+1}/{retries})")
                        time.sleep(delay)
                        delay *= 2
                    else:
                        print(f"❌ API Error loading active vehicles (Status: {e.response.status_code}): {e}")
                        import traceback
                        traceback.print_exc()
                        return {} # Other API error, return empty
                except Exception as e:
                    print(f"❌ Unexpected error during active vehicle load retry: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    return {} # Other error, return empty
            else: # This else block executes if the loop completes without a 'break' (i.e., all retries failed)
                print("❌ Failed to load active vehicles after multiple retries.")
                return {}


            for i, row in enumerate(records, start=2):  # Rows start at 2 (header is row 1)
                plate = str(row.get("License Plate No.", "")).strip()
                exit_time = str(row.get("Time of Exit", "")).strip()
                
                if plate and not exit_time:
                    active_map[plate] = {
                        'row_index': i,
                        'entry_time': str(row.get("Time of Entry", "")).strip()
                    }
                    
        except Exception as e: # Catch any remaining errors from processing records
            print(f"⚠️ Could not load active vehicles: {str(e)}")
            
        print(f"Loaded {len(active_map)} active vehicles.") # <--- ADDED for clarity
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
        """Update sheet with exit time while preserving license plate"""
        if not self.sheet: # <--- ADD THIS CHECK - Good addition
            print("⚠️ Sheet not connected, cannot update exit.")
            return False

        if plate not in self.active_vehicles:
            print(f"⚠️ Plate {plate} not found in active vehicles for exit update.")
            return False

        vehicle = self.active_vehicles[plate]
        
        # Ensure entry_time is a datetime object
        if isinstance(vehicle['entry_time'], str):
            try:
                entry_dt = datetime.strptime(vehicle['entry_time'], "%Y-%m-%d %H:%M:%S.%f") # Added .%f for microseconds
            except ValueError as e:
                # If the first attempt fails, try without microseconds (for older logs)
                try:
                    entry_dt = datetime.strptime(vehicle['entry_time'], "%Y-%m-%d %H:%M:%S")
                except ValueError as e_no_ms:
                    print(f"❌ Invalid entry_time format for {plate}: {e_no_ms}")
                    return False
        else:
            entry_dt = vehicle['entry_time']

        duration = (exit_time - entry_dt).total_seconds() / 60 # in minutes
        
        # Enforce minimum 1 minute duration (or adjust as needed)
        if duration < 1:
            print(f"⏳ Plate {plate} parked for only {duration:.2f} mins (minimum 1 min required)")
            return False 
        
        try:
            # Find column indices dynamically for robustness
            # This 'headers = self.sheet.row_values(1)' call is good.
            # Make sure self.HEADERS from __init__ is used if already loaded to avoid extra API call.
            # Assuming headers are loaded once in __init__ and stored in self.HEADERS
            if not hasattr(self, 'HEADERS') or not self.HEADERS:
                 self.HEADERS = self.sheet.row_values(1) # Load headers if not already
            
            headers = self.HEADERS # Use the loaded headers
            
            # Use 'Time of Exit' and 'Duration (minutes)' as they are in your sheet
            exit_time_col_idx = headers.index('Time of Exit') + 1 # +1 for 1-based indexing
            duration_col_idx = headers.index('Duration (minutes)') + 1

            exit_time_str = exit_time.strftime("%Y-%m-%d %H:%M:%S")
            
            # --- Retry logic for batch_update ---
            retries = 3
            delay = 1
            for i in range(retries):
                try:
                    # FIX: Construct the A1 notation range string directly
                    # A helper function for col_to_char (equivalent to col_letter)
                    def col_to_char(col_idx):
                        char = ""
                        while col_idx > 0:
                            col_idx, remainder = divmod(col_idx - 1, 26)
                            char = chr(65 + remainder) + char
                        return char

                    exit_time_col_char = col_to_char(exit_time_col_idx)
                    duration_col_char = col_to_char(duration_col_idx)
                    row_index = vehicle['row_index']

                    self.sheet.batch_update([{
                        'range': f"{exit_time_col_char}{row_index}", # CORRECTED LINE
                        'values': [[exit_time_str]]
                    }, {
                        'range': f"{duration_col_char}{row_index}", # CORRECTED LINE
                        'values': [[f"{duration:.2f}"]]
                    }])
                    
                    # Remove from active vehicles
                    del self.active_vehicles[plate]
                    print(f"🔴 EXIT: {plate} | Duration: {duration:.2f} mins")
                    return True
                except APIError as e:
                    if e.response.status_code == 503:
                        print(f"❌ API Error [503] updating exit for {plate}. Retrying in {delay}s (Attempt {i+1}/{retries})")
                        time.sleep(delay)
                        delay *= 2
                    else:
                        print(f"❌ API Error updating exit for {plate} (Status: {e.response.status_code}): {e}")
                        traceback.print_exc()
                        return False # Other API error, don't retry immediately
                except Exception as e:
                    print(f"❌ Unexpected error updating exit for {plate}: {str(e)}")
                    traceback.print_exc()
                    return False
            print(f"❌ Failed to update exit for {plate} after multiple retries.")
            return False

        except Exception as e: # Catch any errors from header lookup or other issues
            print(f"❌ Error updating exit for {plate}: {str(e)}")
            traceback.print_exc()
            return False

    
    def _create_entry(self, plate: str, entry_time: datetime, entry_point: str) -> bool:
        """Create new vehicle entry in the sheet"""
        if not self.sheet: # <--- ADD THIS CHECK
            print("⚠️ Sheet not connected, cannot create entry.")
            return False

        try:
            new_row = [
                entry_time.strftime("%Y-%m-%d %H:%M:%S"),  # Time of Entry
                "",  # Time of Exit
                plate,  # License Plate
                "",  # Duration
                entry_point  # Entry Point
            ]
            
            # --- Retry logic for append_row ---
            retries = 3
            delay = 1
            for i in range(retries):
                try:
                    self.sheet.append_row(new_row)
                    # To get the exact new row index, you'd need to fetch all records again or rely on append_row's return if it provided it.
                    # gspread's append_row doesn't directly return the row index.
                    # A common way is to get the total number of rows after appending.
                    # This might be slightly off if multiple things are writing concurrently.
                    new_index = self.sheet.row_count # This gets total rows in the sheet
                    
                    # Update active vehicles cache
                    self.active_vehicles[plate] = {
                        'row_index': new_index,
                        'entry_time': new_row[0]
                    }
                    
                    print(f"🟢 ENTRY: {plate} at {new_row[0]}")
                    return True
                except APIError as e:
                    if e.response.status_code == 503:
                        print(f"❌ API Error [503] creating entry for {plate}. Retrying in {delay}s (Attempt {i+1}/{retries})")
                        time.sleep(delay)
                        delay *= 2
                    else:
                        print(f"❌ API Error creating entry for {plate} (Status: {e.response.status_code}): {e}")
                        import traceback
                        traceback.print_exc()
                        return False # Other API error, no more retries
                except Exception as e:
                    print(f"❌ Unexpected error creating entry for {plate}: {str(e)}")
                    import traceback
                    traceback.print_exc()
                    return False
            print(f"❌ Failed to create entry for {plate} after multiple retries.")
            return False
            # --- End retry logic ---

        except Exception as e: # Catch any remaining errors
            print(f"❌ Error creating entry for {plate}: {str(e)}")
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
        # <--- ADD THIS CHECK AT THE VERY BEGINNING
        if not self.sheet:
            print("⚠️ Google Sheet not connected. Cannot log data.")
            return False

        if not plate_text or not plate_text.strip():
            print("⚠️ Empty or invalid plate text provided")
            return False

        plate_text = plate_text.strip().upper()
        entry_point = entry_point or DEFAULT_ENTRY_POINT
        current_time = datetime.now()

        try:
            # REMOVE THIS LINE: self._verify_headers()
            # Headers are now verified once during _connect_to_sheet
            
            if plate_text in self.active_vehicles:
                return self._update_exit(plate_text, current_time)
            else:
                return self._create_entry(plate_text, current_time, entry_point)
                
        except Exception as e:
            print(f"❌ Unexpected error logging {plate_text}: {str(e)}")
            import traceback # <--- ADD for more detail
            traceback.print_exc() # <--- ADD for more detail
            return False