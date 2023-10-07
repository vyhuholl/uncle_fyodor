"""Configuration variables."""

import os

from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.environ["BOT_TOKEN"]

OPENAI_API_KEY = os.environ["OPENAI_API_KEY"]
HUGGINGFACE_API_KEY = os.environ["OPENAI_API_KEY"]
