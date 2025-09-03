# app/config.py
# Application configuration settings.

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

APP_NAME = "ScamBot Backend"
APP_VERSION = os.getenv("APP_VERSION", "0.1.0")
