from django.db import migrations, models


def backfill_availability_from_stock(apps, schema_editor):
    Product = apps.get_model("myapp", "Product")
    for product in Product.objects.all():
        product.is_available = product.stock > 0
        product.save(update_fields=["is_available"])


class Migration(migrations.Migration):

    dependencies = [
        ("myapp", "0020_restaurant_category_backfill"),
    ]

    operations = [
        migrations.AddField(
            model_name="product",
            name="is_available",
            field=models.BooleanField(default=True),
        ),
        migrations.RunPython(backfill_availability_from_stock, migrations.RunPython.noop),
        migrations.RemoveField(
            model_name="product",
            name="stock",
        ),
    ]
