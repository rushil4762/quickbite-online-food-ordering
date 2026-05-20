from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('myapp', '0015_review_delete_testimonial'),
    ]

    operations = [
        migrations.AddField(
            model_name='profile',
            name='role',
            field=models.CharField(
                choices=[('user', 'User'), ('delivery', 'Delivery Partner')],
                default='user',
                max_length=20,
            ),
        ),
        migrations.CreateModel(
            name='DeliveryPartner',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('phone', models.CharField(max_length=10)),
                ('vehicle_type', models.CharField(
                    choices=[('bike', 'Bike'), ('scooter', 'Scooter'), ('car', 'Car')],
                    max_length=20,
                )),
                ('is_approved', models.BooleanField(default=False)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('profile', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='delivery_partner', to='myapp.profile')),
                ('user', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='delivery_partner', to=settings.AUTH_USER_MODEL)),
            ],
        ),
    ]
