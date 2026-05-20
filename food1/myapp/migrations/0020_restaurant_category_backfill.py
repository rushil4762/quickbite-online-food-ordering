from django.db import migrations


CATEGORY_MAP = {
    "Vegetable": "Fast Food",
    "Fruit": "Desserts",
    "Beverages": "Beverages",
}


def backfill_restaurant_categories(apps, schema_editor):
    Product = apps.get_model("myapp", "Product")
    Cart = apps.get_model("myapp", "Cart")
    OrderItem = apps.get_model("myapp", "OrderItem")

    for old_value, new_value in CATEGORY_MAP.items():
        Product.objects.filter(category=old_value).update(category=new_value)
        Cart.objects.filter(category=old_value).update(category=new_value)
        OrderItem.objects.filter(category=old_value).update(category=new_value)


class Migration(migrations.Migration):

    dependencies = [
        ("myapp", "0019_alter_product_category"),
    ]

    operations = [
        migrations.RunPython(backfill_restaurant_categories, migrations.RunPython.noop),
    ]
