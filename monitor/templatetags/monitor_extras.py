from django import template
from django.utils import timezone
from datetime import timedelta

register = template.Library()

@register.filter
def human_time(value):
    """
    Formats a datetime object to a human-readable string based on specific rules:
    - <= 1 min: "recién"
    - < 2 min: "hace 1 minuto"
    - < 60 min: "hace X minutos"
    - 60 min (59.5-60.5): "hace 1 hora"
    - 90 min (89.5-90.5): "hace hora y media"
    - > 2 hours and today: "hoy a las HH:MM"
    - Yesterday: "ayer a las HH:MM"
    - This week (but before yesterday): "el [Lunes] a las HH:MM"
    - > 1 week: "DD/MM/YYYY" (implied date format via strftime)
    """
    if not value:
        return "Nunca"

    now = timezone.now()
    if now.tzinfo and not value.tzinfo:
        value = timezone.make_aware(value, now.tzinfo)
    
    diff = now - value
    seconds = diff.total_seconds()
    minutes = int(seconds // 60)

    # <= 1 min or < 60 seconds -> "recién"
    if seconds <= 60:
        return "recién"

    # < 2 min (61 to 119 seconds) -> "hace 1 minuto"
    if minutes < 2:
        return "hace 1 minuto"

    # Specific cases for 45, 60, 90 minutes with some tolerance?
    # User said "si fue hace 60 minutos poner 'hace 1 hora'". 
    # Let's handle ranges basically.
    
    # 60 min case (approx 55 to 65 mins maybe? Let's go strict or small range)
    if 58 <= minutes <= 62:
        return "hace 1 hora"
    
    # 90 min case
    if 88 <= minutes <= 92:
        return "hace hora y media"

    # < 60 min -> "hace X minutos"
    if minutes < 60:
        return f"hace {minutes} minutos"
        
    local_now = timezone.localtime(now)
    local_value = timezone.localtime(value)
    
    todays_date = local_now.date()
    value_date = local_value.date()
    
    time_str = local_value.strftime('%H:%M')

    # > 2 hours logic is implicit if we pass the minutes checks above, 
    # but we need to check if it's still today.
    if value_date == todays_date:
        return f"hoy a las {time_str}"
        
    yesterday_date = todays_date - timedelta(days=1)
    if value_date == yesterday_date:
        return f"ayer a las {time_str}"
        
    week_start_date = todays_date - timedelta(days=6)
    if value_date >= week_start_date:
        # Before yesterday but within last week
        days_map = {
            0: 'lunes', 1: 'martes', 2: 'miércoles', 3: 'jueves', 
            4: 'viernes', 5: 'sábado', 6: 'domingo'
        }
        day_name = days_map[local_value.weekday()]
        return f"el {day_name} a las {time_str}"
        
    # Older than a week
    return local_value.strftime("%d/%m/%Y")

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
