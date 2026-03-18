from django import template

register = template.Library()

@register.filter(name='hex_to_rgba')
def hex_to_rgba(hex_color, alpha):
    """
    Converts a hex color string to an rgba string.
    Example: {{ '#FF0000'|hex_to_rgba:0.5 }} -> 'rgba(255, 0, 0, 0.5)'
    """
    hex_color = hex_color.lstrip('#')
    try:
        if len(hex_color) == 3:
            hex_color = ''.join([c*2 for c in hex_color])
        r, g, b = tuple(int(hex_color[i:i+2], 16) for i in (0, 2, 4))
        return f'rgba({r}, {g}, {b}, {alpha})'
    except (ValueError, IndexError):
        # Return a dark default if the hex is invalid
        return f'rgba(0, 0, 0, {alpha})'
