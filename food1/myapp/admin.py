from django.contrib import admin
from .models import Profile, DeliveryPartner
from myapp.models import Contact
from myapp.models import Product
from myapp.models import Order
from myapp.models import OrderItem
from .models import Review
from myapp.models import Cart
# Cart.objects.all()
from myapp.models import Card
from django.http import HttpResponse
from django.contrib import admin
from django.utils import timezone

from django.http import HttpResponse
import io

from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4

class ContactAdmin(admin.ModelAdmin):
    list_display=['id','name','email','subject','message','is_approved','added_on']

class ProfileAdmin(admin.ModelAdmin):
    list_display=['id','name','email','role','contact_number','is_active']


class DeliveryPartnerAdmin(admin.ModelAdmin):
    list_display = ['id', 'profile', 'phone', 'vehicle_type', 'is_approved', 'created_at']
    list_filter = ['is_approved', 'vehicle_type']
    search_fields = ['profile__name', 'profile__email', 'phone']
  
class ProductAdmin(admin.ModelAdmin):
    list_display=['id','name','price','unit','min_quantity','category','is_available','discount_percent']
    list_filter = ['category', 'unit', 'is_available']
    list_editable = ['unit', 'min_quantity', 'is_available']
    


class PaymentMethodFilter(admin.SimpleListFilter):
    title = "Payment Method"
    parameter_name = "payment_method"

    def lookups(self, request, model_admin):
        return [
            ('COD', 'Cash on Delivery'),
            ('UPI', 'Scanner / UPI'),
            ('Card', 'Card Payment'),
        ]

    def queryset(self, request, queryset):
        if self.value():
            return queryset.filter(payment_method=self.value())
        return queryset
    
class OrderAdmin(admin.ModelAdmin):
    list_display = [
        'id', 'profile', 'assigned_delivery_partner', 'order_date', 'delivery_date', 'total_amount',
        'status', 'flat', 'street', 'city', 'pincode', 'payment_method'
    ]
    list_filter = (PaymentMethodFilter,)
    actions = ["download_payment_report"]

    # PDF download action
    def download_payment_report(self, request, queryset):
        response = HttpResponse(content_type="application/pdf")
        response["Content-Disposition"] = "attachment; filename=payment_report.pdf"

        doc = SimpleDocTemplate(response, pagesize=A4)
        styles = getSampleStyleSheet()
        elements = []

        # Report title
        title = Paragraph(
            "<b><font size=16>Payment Report</font></b><br/>"
            f"<font size=11>Generated on: {timezone.now().strftime('%d-%m-%Y %H:%M')}</font>",
            styles["Title"]
        )
        elements.append(title)
        elements.append(Paragraph("<br/>", styles["Normal"]))

        # Table header including address
        data = [["User Name", "Payment Type", "Amount (₹)", "Flat", "Street", "City", "Pincode"]]

        total_amount = 0
        for order in queryset:
            data.append([
                order.profile.name,
                order.payment_method,
                f"₹{order.total_amount}",
                order.flat,
                order.street,
                order.city,
                order.pincode
            ])
            total_amount += order.total_amount

        # Footer row for total
        data.append(["", "Total Amount", f"₹{total_amount}", "", "", "", ""])

        # Table styling
        table = Table(data, colWidths=[120, 100, 80, 80, 100, 80, 60])
        table.setStyle(TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.lightgreen),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.black),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTSIZE", (0, 0), (-1, 0), 12),
            ("ALIGN", (1, 1), (-1, -1), "CENTER"),
            ("GRID", (0, 0), (-1, -1), 0.8, colors.grey),
            ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
        ]))

        elements.append(table)
        doc.build(elements)
        return response

    download_payment_report.short_description = "Download Payment Report (PDF)"
    
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ['id', 'order', 'product_name', 'category', 'unit', 'price', 'quantity']


    




class CartAdmin(admin.ModelAdmin):
    list_display = ['id', 'profile', 'product', 'get_product_name', 'get_category', 'get_unit', 'price_at_time', 'quantity', 'added_at']

    def get_product_name(self, obj):
        return obj.product.name  
    get_product_name.short_description = 'Product Name'

    def get_category(self, obj):
        return obj.product.category  
    get_category.short_description = 'Category'

    def get_unit(self, obj):
        return obj.unit
    get_unit.short_description = 'Unit'


class CardAdmin(admin.ModelAdmin):
    list_display=['id','profile','card_name','card_number_last4','expiry','created_at']  

class ReviewAdmin(admin.ModelAdmin):
    list_display = ('client_name', 'profession', 'created_at')
    
admin.site.register(Profile,ProfileAdmin)
admin.site.register(DeliveryPartner, DeliveryPartnerAdmin)
admin.site.register(Contact,ContactAdmin)
admin.site.register(Product,ProductAdmin)
admin.site.register(Order,OrderAdmin)
admin.site.register(OrderItem,OrderItemAdmin)
admin.site.register(Cart,CartAdmin)
admin.site.register(Card,CardAdmin)


    

# Register your models here.

#jalkapani11
