import json
import requests
import datetime
from pathlib import Path
import pytz
import time
import logging

# Configure logging
logger = logging.getLogger(__name__)

def load_config():
    config_path = Path(__file__).parent / "config.json"
    with open(config_path) as f:
        return json.load(f)

def parse_meteo_lt_time(dt_str):
    fmts = ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"]
    for fmt in fmts:
        try:
            return datetime.datetime.strptime(dt_str, fmt).replace(tzinfo=datetime.timezone.utc)
        except:
            pass
    raise ValueError(f"Bad time format: {dt_str}")

# Enhanced cache mechanism
weather_cache = {
    'data': None,
    'timestamp': 0,
    'last_successful_fetch': 0,
    'error_count': 0,
    'last_error': None
}

def should_refresh_cache():
    """Determine if we should refresh the cache based on various factors"""
    now = time.time()
    config = load_config()
    
    # If we have no data, we should refresh
    if weather_cache['data'] is None:
        return True
        
    # Check if we're past the 2-hour mark from last successful fetch
    if now - weather_cache['last_successful_fetch'] >= 7200:  # 2 hours in seconds
        return True
        
    # If we have errors and it's been more than 5 minutes since last try
    if weather_cache['error_count'] > 0 and now - weather_cache['timestamp'] >= 300:
        return True
        
    return False

def get_weather(config=None):
    if config is None:
        config = load_config()
    api_base_url = config.get('api', {}).get('base_url', "https://api.meteo.lt/v1")
    location = config.get('api', {}).get('location', 'vilnius-paneriai')
    url = f"{api_base_url}/places/{location}/forecasts/long-term"
    
    try:
        logger.info(f"Fetching weather data from {url}")
        r = requests.get(url, timeout=10)  # Add timeout
        if r.status_code != 200:
            error_msg = f"API returned status code {r.status_code}"
            logger.error(error_msg)
            weather_cache['last_error'] = error_msg
            weather_cache['error_count'] += 1
            return weather_cache['data'] if weather_cache['data'] else {}
            
        data = r.json()
        forecasts = data.get("forecastTimestamps", [])
        
        if not forecasts:
            error_msg = "No forecast data received"
            logger.error(error_msg)
            weather_cache['last_error'] = error_msg
            weather_cache['error_count'] += 1
            return weather_cache['data'] if weather_cache['data'] else {}
        
        # Process the data as before...
        now_utc = datetime.datetime.now(datetime.timezone.utc)
        vilnius_tz = pytz.timezone('Europe/Vilnius')
        current_weather = None
        min_diff = None
        
        for entry in forecasts:
            entry_time = parse_meteo_lt_time(entry["forecastTimeUtc"])
            diff = (entry_time - now_utc).total_seconds()
            if diff >= 0 and (min_diff is None or diff < min_diff):
                min_diff = diff
                current_weather = entry
                
        if not current_weather and forecasts:
            current_weather = forecasts[-1]
            entry_time = parse_meteo_lt_time(current_weather["forecastTimeUtc"])
        else:
            entry_time = parse_meteo_lt_time(current_weather["forecastTimeUtc"])
            
        local_time = entry_time.astimezone(vilnius_tz)
        current_weather_data = {
            "dt": int(local_time.timestamp()),
            "forecastTimeUtc": local_time.strftime("%Y-%m-%d %H:%M"),
            "temperature": current_weather["airTemperature"],
            "feelsLike": current_weather["feelsLikeTemperature"],
            "windSpeed": current_weather["windSpeed"],
            "pressure": current_weather["seaLevelPressure"],
            "humidity": current_weather["relativeHumidity"],
            "precipitation": current_weather["totalPrecipitation"],
            "conditionCode": current_weather["conditionCode"]
        }
        
        by_date = {}
        for entry in forecasts:
            dt_obj = parse_meteo_lt_time(entry["forecastTimeUtc"])
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
                    
                dt_obj = parse_meteo_lt_time(f["forecastTimeUtc"])
                midday = dt_obj.replace(hour=12, minute=0, second=0, microsecond=0)
                diff = abs((dt_obj - midday).total_seconds()) / 3600.0
                if diff < best_diff:
                    best_diff = diff
                    best_condition = f["conditionCode"]
                    best_dt_obj = dt_obj
                    
            if not best_dt_obj:
                f0 = daily_entries[0]
                best_dt_obj = parse_meteo_lt_time(f0["forecastTimeUtc"])
                best_condition = f0["conditionCode"]
                
            daily_list.append({
                "dt": int(best_dt_obj.timestamp()),
                "main": {"temp_min": min_temp, "temp_max": max_temp},
                "weather": [{"description": best_condition}]
            })
            
        daily_list = daily_list[:7]  # Get only 7 days forecast
        result = {"daily": daily_list, "current": current_weather_data}
        
        # Update cache with successful data
        weather_cache['data'] = result
        weather_cache['timestamp'] = time.time()
        weather_cache['last_successful_fetch'] = time.time()
        weather_cache['error_count'] = 0
        weather_cache['last_error'] = None
        
        return result
        
    except Exception as e:
        error_msg = f"Error fetching weather data: {str(e)}"
        logger.error(error_msg)
        weather_cache['last_error'] = error_msg
        weather_cache['error_count'] += 1
        return weather_cache['data'] if weather_cache['data'] else {}

def get_weather_data():
    """Get weather data with enhanced caching"""
    if should_refresh_cache():
        return get_weather()
    return weather_cache['data']

def api_data():
    """API endpoint for getting weather data"""
    return get_weather_data()

def api_status():
    """API endpoint for getting cache status"""
    return {
        'last_update': weather_cache['timestamp'],
        'last_successful_fetch': weather_cache['last_successful_fetch'],
        'error_count': weather_cache['error_count'],
        'last_error': weather_cache['last_error'],
        'has_data': weather_cache['data'] is not None
    }

def api_day(timestamp):
    """API endpoint for getting weather for a specific day"""
    data = get_weather_data()
    from datetime import datetime
    target_date = datetime.utcfromtimestamp(timestamp).date()
    for day in data.get('daily', []):
        day_date = datetime.utcfromtimestamp(day['dt']).date()
        if day_date == target_date:
            return day
    return {'error': 'No forecast for this day'}

def api_current():
    """API endpoint for getting detailed current weather data"""
    data = get_weather_data()
    return data.get('current', {}) if data else {}

def get_refresh_interval():
    """Get the refresh interval from config"""
    config = load_config()
    return config.get('updateInterval', 3600)

def init(config):
    """Initialize the plugin as a service-only provider"""
    # This plugin now serves only as a backend API provider
    # No UI initialization needed
    return {'data': {}} 