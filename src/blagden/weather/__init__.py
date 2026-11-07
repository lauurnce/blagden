"""Forecast weather, WBGT, heat index and risk labels for race venues.

Training insight, not a go or no-go decision. Weather data by Open-Meteo.com.
"""

from blagden.weather.heat_index import PAGASA_CATEGORIES, heat_index_c, pagasa_category
from blagden.weather.openmeteo import HourlyWeather, OpenMeteoClient, WeatherError
from blagden.weather.race_morning import RaceHour, RaceMorning, format_race_morning, race_morning
from blagden.weather.risk import RiskLabel, risk_label
from blagden.weather.solar import SunPosition, cos_zenith, sun_position
from blagden.weather.wbgt import WbgtResult, outdoor_wbgt

__all__ = [
    "PAGASA_CATEGORIES",
    "HourlyWeather",
    "OpenMeteoClient",
    "RaceHour",
    "RaceMorning",
    "RiskLabel",
    "SunPosition",
    "WbgtResult",
    "WeatherError",
    "cos_zenith",
    "format_race_morning",
    "heat_index_c",
    "outdoor_wbgt",
    "pagasa_category",
    "race_morning",
    "risk_label",
    "sun_position",
]
