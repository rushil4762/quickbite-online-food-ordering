from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("myapp", "0023_remove_order_payment_status_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="product",
            name="category",
            field=models.CharField(
                choices=[
                    ("Fast Food", "Fast Food"),
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
