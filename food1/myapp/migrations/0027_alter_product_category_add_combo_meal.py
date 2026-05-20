from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("myapp", "0026_backfill_product_units_by_name"),
    ]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="category",
            field=models.CharField(
                choices=[
                    ("Fast Food", "Fast Food"),
                    ("Combo Meal", "Combo Meal"),
                    ("Punjabi Delights", "Punjabi Delights"),
                    ("South Indian", "South Indian"),
                    ("Desserts", "Desserts"),
                    ("Beverages", "Beverages"),
                ],
                default="Fast Food",
                max_length=50,
            ),
        ),
    ]
