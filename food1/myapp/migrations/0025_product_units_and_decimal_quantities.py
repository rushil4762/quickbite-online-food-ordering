from django.db import migrations, models


def backfill_units(apps, schema_editor):
    Product = apps.get_model("myapp", "Product")
    Cart = apps.get_model("myapp", "Cart")
    OrderItem = apps.get_model("myapp", "OrderItem")

    Product.objects.filter(unit="").update(unit="piece")
    Product.objects.filter(min_quantity__lte=0).update(min_quantity=1)

    for cart_item in Cart.objects.select_related("product"):
        cart_item.unit = getattr(cart_item.product, "unit", "piece") or "piece"
        cart_item.save(update_fields=["unit"])

    for order_item in OrderItem.objects.select_related("product"):
        order_item.unit = getattr(order_item.product, "unit", "piece") or "piece"
        order_item.save(update_fields=["unit"])


class Migration(migrations.Migration):

    dependencies = [
        ("myapp", "0024_alter_product_category_add_regional_choices"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="min_quantity",
            field=models.FloatField(default=1),
        ),
        migrations.AddField(
            model_name="product",
            name="unit",
            field=models.CharField(
                choices=[
                    ("kg", "Kilogram"),
                    ("plate", "Plate"),
                    ("piece", "Piece"),
                    ("scoop", "Scoop"),
                    ("packet", "Packet"),
                    ("cup", "Cup"),
                    ("can", "Can"),
                ],
                default="piece",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="cart",
            name="unit",
            field=models.CharField(
                choices=[
                    ("kg", "Kilogram"),
                    ("plate", "Plate"),
                    ("piece", "Piece"),
                    ("scoop", "Scoop"),
                    ("packet", "Packet"),
                    ("cup", "Cup"),
                    ("can", "Can"),
                ],
                default="piece",
                max_length=10,
            ),
        ),
        migrations.AddField(
            model_name="orderitem",
            name="unit",
            field=models.CharField(
                choices=[
                    ("kg", "Kilogram"),
                    ("plate", "Plate"),
                    ("piece", "Piece"),
                    ("scoop", "Scoop"),
                    ("packet", "Packet"),
                    ("cup", "Cup"),
                    ("can", "Can"),
                ],
                default="piece",
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="product",
            name="price",
            field=models.DecimalField(decimal_places=2, max_digits=10),
        ),
        migrations.AlterField(
            model_name="cart",
            name="price_at_time",
            field=models.DecimalField(decimal_places=2, max_digits=10),
        ),
        migrations.AlterField(
            model_name="cart",
            name="quantity",
            field=models.FloatField(default=1),
        ),
        migrations.AlterField(
            model_name="orderitem",
            name="price",
            field=models.DecimalField(decimal_places=2, max_digits=10),
        ),
        migrations.AlterField(
            model_name="orderitem",
            name="quantity",
            field=models.FloatField(default=1),
        ),
        migrations.RunPython(backfill_units, migrations.RunPython.noop),
    ]
