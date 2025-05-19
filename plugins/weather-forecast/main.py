import json
import requests
import datetime
from pathlib import Path

def load_config():
    config_path = Path(__file__).parent / "config.json"
    with open(config_path) as f:
        return json.load(f)

def parse_meteo_lt_time(dt_str):
    fmts = ["%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S"]
    for fmt in fmts:
        try:
            return datetime.datetime.strptime(dt_str, fmt)
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
        return {"daily": daily_list}
    except Exception as e:
        print(f"Error fetching weather data: {e}")
        return {}

def api_data():
    return get_weather()

def get_refresh_interval():
    config = load_config()
    return config.get('updateInterval', 3600)

def init(config):
    return {'data': get_weather(config)} 