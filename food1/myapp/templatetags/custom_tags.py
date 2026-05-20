from django import template
register = template.Library()

@register.filter
def to(value, arg):
    return range(value, arg + 1)


@register.filter
def format_quantity(value):
    try:
        numeric_value = float(value)
    except (TypeError, ValueError):
        return value
    if numeric_value.is_integer():
        return int(numeric_value)
    return f"{numeric_value:.2f}".rstrip("0").rstrip(".")


@register.filter
def product_rating(value):
    ratings = ["3.2", "3.6", "3.9", "4.1", "4.4", "4.7", "4.9"]
    try:
        index = int(value) % len(ratings)
    except (TypeError, ValueError):
        index = 0
    return ratings[index]
