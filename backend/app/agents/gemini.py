"""Shared Gemini client for the research agents."""

from dotenv import load_dotenv
from google import genai

load_dotenv()

client = genai.Client()  # reads GOOGLE_API_KEY from the environment
