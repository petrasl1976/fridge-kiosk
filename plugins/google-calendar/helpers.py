"""
Helper functions for the Google Calendar plugin
"""

def get_event_color(summary):
    """Get a color for an event based on the first two characters
    This is a placeholder, the actual colors will be applied via JavaScript
    using window.KIOSK_CONFIG.userColors
    """
    if not summary:
        return "#673AB7"  # Default color for empty summaries
    return "#673AB7"  # Default - actual color will be applied in frontend

def slice_string(value, start, end=None):
    """Extract a slice of a string"""
    if not value:
        return ""
    if end:
        return value[start:end]
    return value[start:]

def format_time(timestamp_str):
    """Extract just the time part (HH:MM) from an ISO format timestamp"""
    if not timestamp_str:
        return ""
    # For dateTime format: "2024-05-20T14:30:00Z" or similar
    if "T" in timestamp_str:
        time_part = timestamp_str.split("T")[1]
        return time_part[:5]  # Take just HH:MM
    return ""  # Return empty string for all-day events 