import gspread
from oauth2client.service_account import ServiceAccountCredentials

scope = [
          'https://www.googleapis.com/auth/spreadsheets',
          'https://www.googleapis.com/auth/drive.file',
          'https://www.googleapis.com/auth/drive'
        ]

try:
    creds = ServiceAccountCredentials.from_json_keyfile_name('platetrackerfullaccess-8e6fbccc7a40.json', scope)
    client = gspread.authorize(creds)
    
    # Test API access
    print("Available spreadsheets:")
    for sheet in client.list_spreadsheet_files():
        print(f"- {sheet['name']} (ID: {sheet['id']})")
    
    print("\nTest successful! APIs are properly configured.")
except Exception as e:
    print(f"FAILED: {str(e)}")
    print("\nTroubleshooting:")
    print("1. Verify service_account.json exists")
    print("2. Check spreadsheet sharing permissions")
    print("3. Confirm APIs are enabled in Google Cloud")