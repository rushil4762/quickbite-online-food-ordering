from django.db import migrations


UNIT_RULES = [
    ("can", ["coca-cola", "coca cola", "coke", "pepsi", "sprite", "fanta"]),
    ("cup", ["coffee", "tea", "chai"]),
    ("packet", ["biscuit", "biscuits", "chips", "namkeen", "wafer"]),
    ("scoop", ["ice cream", "kulfi", "gelato", "sundae"]),
    ("kg", ["paneer", "sabji", "sabzi", "tikka masala", "gravy", "curry"]),
    ("plate", ["bhaji pav", "bhajipav", "thali", "dosa", "dhosa", "idli", "uttapam", "upma", "poha"]),
    ("piece", ["pizza", "sandwich", "cookie", "cookies", "cake", "pastry", "dabeli", "vadapav", "vada pav", "frankie"]),
]


def infer_unit(product_name):
    name = (product_name or "").strip().lower()
    for unit, keywords in UNIT_RULES:
        if any(keyword in name for keyword in keywords):
            return unit
    return None


def assign_units(apps, schema_editor):
    Product = apps.get_model("myapp", "Product")
    Cart = apps.get_model("myapp", "Cart")
    OrderItem = apps.get_model("myapp", "OrderItem")

    product_unit_map = {}

    for product in Product.objects.all():
        inferred_unit = infer_unit(product.name)
        if not inferred_unit:
            product_unit_map[product.id] = product.unit
            continue

        updates = []
        if product.unit != inferred_unit:
            product.unit = inferred_unit
            updates.append("unit")

        if inferred_unit == "kg" and product.min_quantity < 1:
            product.min_quantity = 1
            updates.append("min_quantity")
        elif inferred_unit != "kg" and product.min_quantity != 1:
            product.min_quantity = 1
            updates.append("min_quantity")

        if updates:
            product.save(update_fields=updates)

        product_unit_map[product.id] = product.unit

    for cart_item in Cart.objects.select_related("product"):
        if cart_item.product_id in product_unit_map:
            cart_item.unit = product_unit_map[cart_item.product_id]
            cart_item.save(update_fields=["unit"])

    for order_item in OrderItem.objects.select_related("product"):
        if order_item.product_id in product_unit_map:
            order_item.unit = product_unit_map[order_item.product_id]
            order_item.save(update_fields=["unit"])


class Migration(migrations.Migration):

    dependencies = [
        ("myapp", "0025_product_units_and_decimal_quantities"),
    ]

    operations = [
        migrations.RunPython(assign_units, migrations.RunPython.noop),
    ]
