"""
Lightweight Weather Client using Open-Meteo (No API Key Required)
"""
import requests
import logging

logger = logging.getLogger(__name__)

WMO_CODES = {
    0: "Clear", 1: "Clear", 2: "Pt Cldy", 3: "Cloudy",
    45: "Fog", 48: "Fog",
    51: "Drizzle", 53: "Drizzle", 55: "Drizzle",
    61: "Rain", 63: "Rain", 65: "Hvy Rain",
    71: "Snow", 73: "Snow", 75: "Hvy Snow",
    80: "Showers", 81: "Showers", 82: "Showers",
    95: "Storm", 96: "Storm", 99: "Storm"
}


class WeatherClient:
    def __init__(self, lat, lon):
        self.url = (
            f"https://open-meteo.com?"
            f"latitude={lat}&longitude={lon}&current_weather=true&temperature_unit=fahrenheit"
        )

    def get_weather(self):
        try:
            resp = requests.get(self.url, timeout=5)
            resp.raise_for_status()
            data = resp.json().get("current_weather", {})
            temp = round(data.get("temperature", 0))
            code = data.get("weathercode", 0)
            condition = WMO_CODES.get(code, "")
            return f"{temp}F {condition}".strip()
        except Exception as e:
            logger.error(f"Error fetching weather: {e}")
            return None
