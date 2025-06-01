import json
import requests
import datetime
from pathlib import Path
import pytz
import time
from flask import Blueprint, jsonify, request

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

def get_weather(config=None):
    if config is None:
        config = load_config()
    api_base_url = config.get('api', {}).get('base_url', "https://api.meteo.lt/v1")
    location = config.get('api', {}).get('location', 'vilnius-paneriai')
    url = f"{api_base_url}/places/{location}/forecasts/long-term"
    try:
        r = requests.get(url)
        if r.status_code != 200:
            return {}
        data = r.json()
        forecasts = data.get("forecastTimestamps", [])
        
        # Find the forecast closest to now (but not earlier)
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
            # fallback: use the last available forecast
            current_weather = forecasts[-1]
            entry_time = parse_meteo_lt_time(current_weather["forecastTimeUtc"])
        else:
            entry_time = parse_meteo_lt_time(current_weather["forecastTimeUtc"])
        # Convert UTC time to Europe/Vilnius
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
        return {"daily": daily_list, "current": current_weather_data}
    except Exception as e:
        print(f"Error fetching weather data: {e}")
        return {}

weather_cache = {
    'data': None,
    'timestamp': 0
}

def get_weather_data():
    config = load_config()
    interval = config.get('updateInterval', 900)
    now = time.time()
    if weather_cache['data'] and (now - weather_cache['timestamp'] < interval):
        return weather_cache['data']
    # Fetch new data from API
    data = get_weather()
    weather_cache['data'] = data
    weather_cache['timestamp'] = now
    return data

# Flask blueprint for plugin API
bp = Blueprint('weather_forecast', __name__)

@bp.route('/api/plugins/weather-forecast/data')
def api_data():
    return jsonify(get_weather_data())

@bp.route('/api/plugins/weather-forecast/day/<int:timestamp>')
def api_day(timestamp):
    data = get_weather_data()
    # Find the daily forecast for the given timestamp (date only)
    from datetime import datetime
    target_date = datetime.utcfromtimestamp(timestamp).date()
    for day in data.get('daily', []):
        day_date = datetime.utcfromtimestamp(day['dt']).date()
        if day_date == target_date:
            return jsonify(day)
    return jsonify({'error': 'No forecast for this day'}), 404

def get_refresh_interval():
    config = load_config()
    return config.get('updateInterval', 3600)

def init(config):
    return {'data': get_weather(config)} 