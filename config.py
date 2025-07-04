"""
# Google Sheets Configuration
SPREADSHEET_ID = "1KTmRQyM5rXHs8ZGFaZbvu6IqWcvRc3QGKwOGN_VbadQ"
WORKSHEET_NAME = 'VehicleLogs'

# Camera Configuration
CAMERA_SOURCE = 0  # 0 for default webcam, or RTSP URL for IP camera
ENTRY_POINT_NAME = "Main Gate"

# Image Processing
PLATE_MIN_AREA = 500  # Minimum area for plate contour
PLATE_RATIO = 3.0     # Width/height ratio for plates

# Debugging
SAVE_IMAGES = False   # Save captured images for debugging
DEBUG_MODE = True     # Show processing windows
"""


"""
# ===============================
# 🔧 Google Sheets Configuration
# ===============================
SPREADSHEET_ID = "1KTmRQyM5rXHs8ZGFaZbvu6IqWcvRc3QGKwOGN_VbadQ"
WORKSHEET_NAME = "VehicleLogs"

# ===============================
# 🎥 Camera Configuration
# ===============================
CAMERA_SOURCE = 0  # 0 = built-in webcam, or use RTSP URL for IP cam
ENTRY_POINT_NAME = "Main Gate"

# ===============================
# 📸 Image Processing Parameters
# ===============================
PLATE_MIN_AREA = 4500  # 🔧 Set to ~4500 for better filtering of real plates
PLATE_RATIO = 2.0      # Plate aspect ratio (width / height)

# ===============================
# 🧪 Debug & Logging
# ===============================
SAVE_IMAGES = True     # Save images for confirmed plate reads
DEBUG_MODE = True      # Show debug windows

"""


# Camera Configuration
CAMERA = {
    'SOURCE': 0,                   # 0 for default webcam, or "rtsp://..." for IP camera
    'RESOLUTION': (1280, 720),     # Higher resolution helps with recognition
    'FOCUS': 30,                   # If camera supports manual focus (0-255)
    'FPS': 60,                     # Target frames per second
    'AUTO_EXPOSURE': False,        # Set to True for automatic exposure adjustment
    'EXPOSURE': 0                  # Manual exposure value if AUTO_EXPOSURE is False
}

# Application Settings
APP = {
    'DEBUG_MODE': True,            # Show processing windows and debug output
    'SAVE_IMAGES': True,           # Save captured images for debugging
    'ENTRY_POINT': "Main Gate",    # Default entry point name
    'LOG_INTERVAL': 120,           # Minimum seconds between logging same plate (anti-spam)
    'PROCESSING_FPS': 1            # Target processing frames per second (reduces CPU load)
}

# License Plate Detection Parameters
PLATE = {
    'MIN_AREA': 1000,              # Reduced for smaller/distant plates (from 3000)
    'MAX_AREA': 50000,             # Increased for larger plates (from 30000)
    'MIN_RATIO': 2.5,              # Wider range for angled plates (from 3.5)
    'MAX_RATIO': 6.0,              # Accommodate more plate shapes (from 5.5)
    'MIN_TEXT_LENGTH': 4,          # Allow partial detections (from 6)
    'MAX_TEXT_LENGTH': 12,         # Longer plates (e.g., some EU formats)
    'TEXT_WHITELIST': "ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789"  # No change
}
# Google Sheets Integration
GOOGLE_SHEETS = {
    'SPREADSHEET_ID': '1KTmRQyM5rXHs8ZGFaZbvu6IqWcvRc3QGKwOGN_VbadQ',
    'WORKSHEET_NAME': 'VehicleLogs',
    'CREDENTIALS_FILE': 'platetrackerfullaccess-8e6fbccc7a40.json',
    'HEADERS': [
        "Time of Entry",
        "Time of Exit",
        "License Plate No.",
        "Duration (minutes)",
        "Entry Point"
    ]
}

# Image Processing
IMAGE = {
    'SAVE_PATH': 'captures',       # Directory to save captured images
    'SAVE_FORMAT': 'jpg',          # Image format for saved captures
    'QUALITY': 95,                 # JPEG quality percentage (1-100)
    'MAX_STORAGE_MB': 500,         # Maximum storage to use for captures (MB)
    'PRUNE_DAYS': 30               # Automatically delete images older than X days
}

# Notification Settings (optional)
NOTIFICATIONS = {
    'ENABLED': False,              # Enable/disable notifications
    'NEW_ENTRY_WEBHOOK': None,     # Webhook URL for new entries
    'EXIT_WEBHOOK': None,          # Webhook URL for exits
    'ERROR_WEBHOOK': None          # Webhook URL for errors
}