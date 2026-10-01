from mcp.server.fastmcp import FastMCP
import requests
from dotenv import load_dotenv
import os

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")

mcp = FastMCP(name="Weather MCP")

@mcp.tool()
def get_current_weather(city: str):
    url = f"https://api.openweathermap.org/data/2.5/weather"
    response = requests.get(url, params={"q": city, "appid": OPENWEATHER_API_KEY, 
    "units": "metric"})
    if response.status_code != 200:
        return {"error": "Failed to get weather data"}
    data =response.json()
    return {
       "city": data["name"],
       "temperature_c": data["main"]["temp"],
       "feels_like_c": data["main"]["feels_like"],
       "humidity": data["main"]["humidity"],
       "condition": data["weather"][0]["description"],
       "wind_speed": data["wind"]["speed"],
    }

@mcp.tool()
def get_forecast(city: str):
    url = f"https://api.openweathermap.org/data/2.5/forecast"
    response = requests.get(url, params={"q": city, "appid": OPENWEATHER_API_KEY, 
    "units": "metric"})
    if response.status_code != 200:
        return {"error": "Failed to get forecast data"}
    data = response.json()
    forecast = []
    for item in data["list"][:5]:
        forecast.append({
            "datetime": item["dt_txt"],
            "temperature": item["main"]["temp"],
            "weather": item["weather"][0]["description"]
        })
    return forecast

if __name__ == "__main__":
    mcp.run(transport="stdio")