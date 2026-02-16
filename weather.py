"""Weather fetching utilities for packing assistant."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import List
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import urlopen
import json

GEOCODING_URL = "https://geocoding-api.open-meteo.com/v1/search"
FORECAST_URL = "https://api.open-meteo.com/v1/forecast"


class WeatherError(Exception):
    """Raised when weather data could not be fetched or parsed."""


@dataclass
class DailyWeather:
    """Daily weather summary for a date."""

    forecast_date: date
    temp_max_c: float
    temp_min_c: float
    precipitation_mm: float
    wind_max_kmh: float


@dataclass
class Location:
    """Resolved location from Open-Meteo geocoding."""

    name: str
    country: str
    latitude: float
    longitude: float


@dataclass
class WeatherBundle:
    """Location and weather forecasts together."""

    location: Location
    daily: List[DailyWeather]


def _get_json(url: str, params: dict[str, str | float | int], timeout: int) -> dict:
    query = urlencode(params)
    request_url = f"{url}?{query}"
    try:
        with urlopen(request_url, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except HTTPError as exc:
        raise WeatherError(f"API returned HTTP {exc.code}.") from exc
    except URLError as exc:
        raise WeatherError(f"Network error: {exc.reason}") from exc

    try:
        payload = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise WeatherError("Invalid JSON response from weather service.") from exc

    if not isinstance(payload, dict):
        raise WeatherError("Unexpected API response structure.")
    return payload


def geocode_city(city: str, timeout: int = 15) -> Location:
    """Resolve city to geographic coordinates using Open-Meteo geocoding."""
    payload = _get_json(
        GEOCODING_URL,
        {"name": city, "count": 1, "language": "en", "format": "json"},
        timeout,
    )

    results = payload.get("results") or []
    if not results:
        raise WeatherError(f"Could not find city '{city}'.")

    top = results[0]
    try:
        return Location(
            name=top["name"],
            country=top.get("country", "Unknown"),
            latitude=float(top["latitude"]),
            longitude=float(top["longitude"]),
        )
    except (KeyError, TypeError, ValueError) as exc:
        raise WeatherError("Geocoding data missing required fields.") from exc


def fetch_daily_weather(location: Location, start_date: date, end_date: date, timeout: int = 20) -> List[DailyWeather]:
    """Fetch daily weather forecast for a location and date range."""
    params = {
        "latitude": location.latitude,
        "longitude": location.longitude,
        "start_date": start_date.isoformat(),
        "end_date": end_date.isoformat(),
        "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum,wind_speed_10m_max",
        "timezone": "auto",
    }
    payload = _get_json(FORECAST_URL, params, timeout)

    daily = payload.get("daily")
    if not daily:
        raise WeatherError("Forecast response did not contain daily data.")

    keys = ["time", "temperature_2m_max", "temperature_2m_min", "precipitation_sum", "wind_speed_10m_max"]
    for key in keys:
        if key not in daily:
            raise WeatherError(f"Forecast data missing '{key}'.")

    rows = zip(
        daily["time"],
        daily["temperature_2m_max"],
        daily["temperature_2m_min"],
        daily["precipitation_sum"],
        daily["wind_speed_10m_max"],
    )

    result: List[DailyWeather] = []
    for day_str, tmax, tmin, precip, wind in rows:
        try:
            result.append(
                DailyWeather(
                    forecast_date=date.fromisoformat(day_str),
                    temp_max_c=float(tmax),
                    temp_min_c=float(tmin),
                    precipitation_mm=float(precip),
                    wind_max_kmh=float(wind),
                )
            )
        except (TypeError, ValueError) as exc:
            raise WeatherError("Unexpected value while parsing forecast data.") from exc

    return result


def get_weather_bundle(city: str, start_date: date, end_date: date) -> WeatherBundle:
    """Fetch location and weather data for city and date range."""
    location = geocode_city(city)
    daily = fetch_daily_weather(location, start_date, end_date)
    return WeatherBundle(location=location, daily=daily)
