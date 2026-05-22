import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN: str = os.getenv("BOT_TOKEN")
HR_ADMIN_ID: int = int(os.getenv("HR_ADMIN_ID"))
REGULAR_ADMIN_IDS: list[int] = [
    int(x.strip())
    for x in os.getenv("REGULAR_ADMIN_IDS", "").split(",")
    if x.strip()
]
ALL_ADMIN_IDS: list[int] = [HR_ADMIN_ID] + REGULAR_ADMIN_IDS
SPREADSHEET_ID: str = os.getenv("SPREADSHEET_ID")
GOOGLE_CREDENTIALS_PATH: str = os.getenv("GOOGLE_CREDENTIALS_PATH", "credentials.json")
