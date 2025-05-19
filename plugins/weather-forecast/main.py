import json
import os
import requests
import datetime
from pathlib import Path

class WeatherForecastPlugin:
    def __init__(self):
        self.config = self._load_config()
        self.api_base_url = "https://api.meteo.lt/v1"
        
    def _load_config(self):
        config_path = Path(__file__).parent / "config.json"
        with open(config_path) as f:
            return json.load(f)
            
    def parse_meteo_lt_time(self, dt_str):
        fmts = ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"]
        for fmt in fmts:
            try:
                return datetime.datetime.strptime(dt_str, fmt)
            except:
                pass
        raise ValueError(f"Bad time format: {dt_str}")
        
    def get_weather(self):
        """Get weather forecast data from meteo.lt API"""
        url = f"{self.api_base_url}/places/{self.config['config']['location']}/forecasts/long-term"
        try:
            r = requests.get(url)
            if r.status_code != 200:
                return None
                
            data = r.json()
            forecasts = data.get("forecastTimestamps", [])
            by_date = {}
            
            for entry in forecasts:
                dt_obj = self.parse_meteo_lt_time(entry["forecastTimeUtc"])
                date_str = dt_obj.strftime("%Y-%m-%d")
                by_date.setdefault(date_str, []).append(entry)
                
            daily_list = []
            for date_str in sorted(by_date.keys()):
                daily_entries = by_date[date_str]
                if not daily_entries:
                    continue
                    
                min_temp, max_temp = None, None
                best_condition, best_dt_obj = None, None
                best_diff = 24
                
                for f in daily_entries:
                    t = f["airTemperature"]
                    if min_temp is None or t < min_temp:
                        min_temp = t
                    if max_temp is None or t > max_temp:
                        max_temp = t
                        
                    dt_obj = self.parse_meteo_lt_time(f["forecastTimeUtc"])
                    midday = dt_obj.replace(hour=12, minute=0, second=0, microsecond=0)
                    diff = abs((dt_obj - midday).total_seconds()) / 3600.0
                    
                    if diff < best_diff:
                        best_diff = diff
                        best_condition = f["conditionCode"]
                        best_dt_obj = dt_obj
                        
                if not best_dt_obj:
                    f0 = daily_entries[0]
                    best_dt_obj = self.parse_meteo_lt_time(f0["forecastTimeUtc"])
                    best_condition = f0["conditionCode"]
                    
                daily_list.append({
                    "dt": int(best_dt_obj.timestamp()),
                    "main": {"temp_min": min_temp, "temp_max": max_temp},
                    "weather": [{"description": best_condition}]
                })
                
            daily_list = daily_list[:7]  # Get only 7 days forecast
            return {"daily": daily_list}
            
        except Exception as e:
            print(f"Error fetching weather data: {e}")
            return None
            
    def get_config(self):
        """Return plugin configuration"""
        return self.config
        
    def get_refresh_interval(self):
        """Return refresh interval in seconds"""
        return self.config['config']['refresh_interval'] 