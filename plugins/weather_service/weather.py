"""
Weather service plugin for Nexus AI Assistant.

This plugin provides weather information for cities around the world.
"""
import requests
import json
import os
import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# Base plugin class (would typically be imported from a common location)
class Plugin:
    """Base class for Nexus plugins."""
    
    async def process(self, request: str, **kwargs) -> Dict[str, Any]:
        """Process a plugin request.
        
        Args:
            request: Request string
            **kwargs: Additional parameters
            
        Returns:
            Processing result
        """
        raise NotImplementedError("Subclasses must implement this")

class WeatherService(Plugin):
    """Weather service plugin that provides current weather information."""
    
    def __init__(self):
        """Initialize weather service plugin."""
        self.api_key = os.getenv("OPENWEATHER_API_KEY", "YOUR_API_KEY")
        self.base_url = "https://api.openweathermap.org/data/2.5"
        self.geocoding_url = "https://api.openweathermap.org/geo/1.0/direct"
        logger.info("Weather service plugin initialized")
        
    async def process(self, request: str, **kwargs) -> Dict[str, Any]:
        """Process a weather request.
        
        Args:
            request: Request string
            **kwargs: Additional parameters
                - plugin_inputs: Dictionary of plugin inputs
                - context: Conversation context
            
        Returns:
            Weather information
        """
        # Get plugin inputs
        plugin_inputs = kwargs.get('plugin_inputs', {})
        
        # Get city from inputs or try to extract from request
        city = plugin_inputs.get('city')
        if not city:
            city = self._extract_city(request)
            
        # If still no city, use default
        if not city:
            city = "New York"
            
        # Get other parameters
        detailed = plugin_inputs.get('detailed', False)
        units = plugin_inputs.get('units', 'metric')
        
        try:
            # Get weather data
            weather_data = await self._get_weather(city, units)
            
            # Get forecast if detailed is requested
            forecast_data = None
            if detailed:
                forecast_data = await self._get_forecast(city, units)
                
            # Format response
            response = self._format_response(weather_data, forecast_data, units)
            
            return {
                "status": "success",
                "data": weather_data,
                "text": response
            }
        except Exception as e:
            logger.error(f"Error getting weather data: {str(e)}")
            return {
                "status": "error",
                "message": f"Error getting weather data: {str(e)}",
                "text": f"Sorry, I couldn't get the weather for {city}. Error: {str(e)}"
            }
            
    def _extract_city(self, request: str) -> Optional[str]:
        """Extract city name from request.
        
        Args:
            request: Request string
            
        Returns:
            City name if found, None otherwise
        """
        # Simple extraction based on common patterns
        city = None
        
        patterns = [
            "weather in ",
            "weather for ",
            "temperature in ",
            "forecast for "
        ]
        
        for pattern in patterns:
            if pattern in request.lower():
                parts = request.lower().split(pattern)
                if len(parts) > 1:
                    city_part = parts[1].strip()
                    # Take the first few words as the city name (up to a punctuation or conjunction)
                    city_words = []
                    for word in city_part.split():
                        if word in ["and", "or", "but", "because", "since"]:
                            break
                        if word.endswith(".") or word.endswith("?") or word.endswith("!"):
                            city_words.append(word[:-1])
                            break
                        city_words.append(word)
                    city = " ".join(city_words)
                    break
                    
        return city
            
    async def _get_weather(self, city: str, units: str = 'metric') -> Dict[str, Any]:
        """Get current weather for a city.
        
        Args:
            city: City name
            units: Temperature units (metric, imperial, standard)
            
        Returns:
            Weather data
        """
        # First try to get coordinates
        coords = await self._get_coordinates(city)
        
        # Make API request
        url = f"{self.base_url}/weather"
        params = {
            "lat": coords["lat"],
            "lon": coords["lon"],
            "appid": self.api_key,
            "units": units
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
        
    async def _get_forecast(self, city: str, units: str = 'metric') -> Dict[str, Any]:
        """Get weather forecast for a city.
        
        Args:
            city: City name
            units: Temperature units (metric, imperial, standard)
            
        Returns:
            Forecast data
        """
        # First try to get coordinates
        coords = await self._get_coordinates(city)
        
        # Make API request
        url = f"{self.base_url}/forecast"
        params = {
            "lat": coords["lat"],
            "lon": coords["lon"],
            "appid": self.api_key,
            "units": units,
            "cnt": 10  # Number of data points (4 per day)
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        return response.json()
        
    async def _get_coordinates(self, city: str) -> Dict[str, float]:
        """Get coordinates for a city.
        
        Args:
            city: City name
            
        Returns:
            Coordinates (lat, lon)
        """
        url = self.geocoding_url
        params = {
            "q": city,
            "limit": 1,
            "appid": self.api_key
        }
        
        response = requests.get(url, params=params)
        response.raise_for_status()
        
        results = response.json()
        if not results:
            raise ValueError(f"City '{city}' not found")
            
        return {
            "lat": results[0]["lat"],
            "lon": results[0]["lon"],
            "name": results[0]["name"],
            "country": results[0]["country"]
        }
        
    def _format_response(self, weather_data: Dict[str, Any], 
                        forecast_data: Optional[Dict[str, Any]], 
                        units: str) -> str:
        """Format weather data into a human-readable response.
        
        Args:
            weather_data: Current weather data
            forecast_data: Forecast data (optional)
            units: Temperature units
            
        Returns:
            Formatted response
        """
        # Get temperature unit symbol
        unit_symbol = "°C" if units == "metric" else "°F" if units == "imperial" else "K"
        
        # Format current weather
        city_name = weather_data.get("name", "Unknown")
        country = weather_data.get("sys", {}).get("country", "")
        
        if country:
            location = f"{city_name}, {country}"
        else:
            location = city_name
            
        temp = weather_data.get("main", {}).get("temp")
        feels_like = weather_data.get("main", {}).get("feels_like")
        description = weather_data.get("weather", [{}])[0].get("description", "").capitalize()
        humidity = weather_data.get("main", {}).get("humidity")
        wind_speed = weather_data.get("wind", {}).get("speed")
        
        # Build response
        response = f"Weather in {location}:\n"
        response += f"• Current Temperature: {temp}{unit_symbol}\n"
        response += f"• Feels Like: {feels_like}{unit_symbol}\n"
        response += f"• Conditions: {description}\n"
        response += f"• Humidity: {humidity}%\n"
        
        # Add wind speed with appropriate unit
        if units == "imperial":
            response += f"• Wind Speed: {wind_speed} mph\n"
        else:
            response += f"• Wind Speed: {wind_speed} m/s\n"
            
        # Add forecast if available
        if forecast_data:
            response += "\nForecast:\n"
            
            # Get daily forecasts (every 8 points is a new day)
            forecasts = forecast_data.get("list", [])
            days = {}
            
            for forecast in forecasts:
                date = forecast.get("dt_txt", "").split(" ")[0]
                if date not in days:
                    days[date] = []
                days[date].append(forecast)
                
            # Add a summary for each day
            for date, day_forecasts in list(days.items())[:3]:  # Limit to 3 days
                # Get average temperature
                avg_temp = sum(f.get("main", {}).get("temp", 0) for f in day_forecasts) / len(day_forecasts)
                
                # Get most common weather condition
                conditions = {}
                for f in day_forecasts:
                    condition = f.get("weather", [{}])[0].get("description", "").capitalize()
                    conditions[condition] = conditions.get(condition, 0) + 1
                    
                most_common_condition = max(conditions.items(), key=lambda x: x[1])[0]
                
                # Format date
                from datetime import datetime
                date_obj = datetime.strptime(date, "%Y-%m-%d")
                formatted_date = date_obj.strftime("%A, %b %d")
                
                response += f"• {formatted_date}: {avg_temp:.1f}{unit_symbol}, {most_common_condition}\n"
                
        return response
