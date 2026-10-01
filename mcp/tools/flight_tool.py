import requests
import os
from dotenv import load_dotenv
load_dotenv()

AVIATIONSTACK_API_KEY = os.getenv("AVIATIONSTACK_API_KEY")

def flight_search(query: str) -> str:
    url = f"https://api.aviationstack.com/v1/flights"
    params = { "access_key": AVIATIONSTACK_API_KEY, "limit": 5 }
    response = requests.get(url, params=params)
    data = response.json()

    flights = []

    if "data" in data:
        for flight in data["data"][:5]:
            airline = flight.get("airline", {}).get("name", "Unknown")
            departure = flight.get("departure", {}).get("airport", "Unknown")
            arrival = flight.get("arrival", {}).get("airport", "Unknown")
            status = flight.get("flight_status", "Unknown")
            flights.append(f" Airline: {airline} Departure: {departure} Arrival: {arrival} Status: {status}")

    return "\n".join(flights)