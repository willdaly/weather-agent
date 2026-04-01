import os
from dotenv import load_dotenv

load_dotenv()

AGENT_ID = os.getenv("AGENT_ID", "mbta-boston-weather-agent")
AGENT_HOST = os.getenv("AGENT_HOST", "0.0.0.0")
AGENT_PORT = int(os.getenv("AGENT_PORT", "8004"))
AGENT_PUBLIC_URL = os.getenv("AGENT_PUBLIC_URL", f"http://localhost:{AGENT_PORT}")
REGISTRY_URL = os.getenv("REGISTRY_URL", "http://localhost:8000")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY", "")
WEATHER_API_BASE_URL = os.getenv("WEATHER_API_BASE_URL", "https://api.openweathermap.org/data/2.5")
WEATHER_DEFAULT_LOCATION = os.getenv("WEATHER_DEFAULT_LOCATION", "Boston, MA")
WEATHER_PROVIDER_NAME = os.getenv("WEATHER_PROVIDER_NAME", "openweathermap")

VERSION = "1.0.0"
