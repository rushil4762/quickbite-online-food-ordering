from django.db import migrations


def assign_existing_orders(apps, schema_editor):
    DeliveryPartner = apps.get_model("myapp", "DeliveryPartner")
    Order = apps.get_model("myapp", "Order")

    partners = list(DeliveryPartner.objects.filter(is_approved=True).order_by("created_at", "id"))
    if not partners:
        return

    partner_index = 0
    for order in Order.objects.filter(assigned_delivery_partner__isnull=True, status="Pending").order_by("id"):
        order.assigned_delivery_partner = partners[partner_index]
        order.save(update_fields=["assigned_delivery_partner"])
        partner_index = (partner_index + 1) % len(partners)


class Migration(migrations.Migration):

    dependencies = [
        ("myapp", "0017_order_assigned_delivery_partner"),
    ]

    operations = [
        migrations.RunPython(assign_existing_orders, migrations.RunPython.noop),
    ]
