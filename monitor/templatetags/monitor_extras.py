from django import template
from django.utils import timezone
from datetime import timedelta

register = template.Library()

@register.filter
def human_time(value):
    """
    Formats a datetime object to a human-readable string based on specific rules:
    - < 1 min: "Recién"
    - < 60 min: "hace X min"
    - Yesterday: "ayer a la HH:MM"
    - < 7 days: "hace X días"
    - > 7 days: Short date format (e.g. 05/10/23)
    """
    if not value:
        return "-"

    now = timezone.now()
    if now.tzinfo and not value.tzinfo:
        value = timezone.make_aware(value, now.tzinfo)
    
    diff = now - value
    seconds = diff.total_seconds()

    if seconds < 60:
        return "recién"

    local_now = timezone.localtime(now)
    local_value = timezone.localtime(value)
    
    today_start = local_now.replace(hour=0, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    week_start = today_start - timedelta(days=6) # Last 6 days + today = 7 days window

    time_str = local_value.strftime('%H:%M')

    if local_value >= today_start:
        return f"hoy a las {time_str}"
        
    if local_value >= yesterday_start:
        return f"ayer a las {time_str}"
        
    if local_value >= week_start:
        # Get Spanish day name
        days_map = {
            0: 'lunes', 1: 'martes', 2: 'miércoles', 3: 'jueves', 
            4: 'viernes', 5: 'sábado', 6: 'domingo'
        }
        day_name = days_map[local_value.weekday()]
        return f"el {day_name} a las {time_str}"
        
    # Older than a week
    return local_value.strftime("%d/%m/%y a las %H:%M")

@register.filter
def get_item(dictionary, key):
    """Get an item from a dictionary by key."""
    if dictionary is None:
        return []
    return dictionary.get(key, [])


@register.filter
def thousands_dot(value):
    """
    Format a number with dot (.) as thousands separator.
    
    Example:
        1000 -> 1.000
        1000000 -> 1.000.000
    """
    try:
        value = int(value)
        return f"{value:,}".replace(',', '.')
    except (ValueError, TypeError):
        return value

@register.filter
def unique_portions(medidores):
    """Returns a list of unique portions from a list/queryset of medidores."""
    if not medidores:
        return []
    
    seen = set()
    portions = []
    
    # Check if medidores is a queryset or list
    iterable = medidores.all() if hasattr(medidores, 'all') else medidores
        
    for medidor in iterable:
        porcion = medidor.porcion
        if porcion and porcion.id not in seen:
            seen.add(porcion.id)
            portions.append(porcion)
            
    # Sort by name
    portions.sort(key=lambda x: x.nombre)
    return portions
