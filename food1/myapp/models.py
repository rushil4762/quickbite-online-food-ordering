from decimal import Decimal

from django.core.exceptions import ValidationError
from django.db import models
from django.contrib.auth.models import User

class Contact(models.Model):
    name=models.CharField(max_length=50)
    email=models.EmailField(max_length=254)
    subject=models.CharField(max_length=250)
    message=models.TextField(max_length=250)
    added_on=models.DateTimeField(auto_now_add=True)
    is_approved=models.BooleanField(default=True)
    
    def __str__(self):
        return self.name
    
    class Meta:
        verbose_name_plural="Contact Table"
    
    
class Profile(models.Model):
    ROLE_USER = 'user'
    ROLE_DELIVERY = 'delivery'
    ROLE_CHOICES = [
        (ROLE_USER, 'User'),
        (ROLE_DELIVERY, 'Delivery Partner'),
    ]

    user=models.OneToOneField(User,on_delete=models.CASCADE,null=True,blank=True)
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)
    contact_number = models.CharField(max_length=10)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default=ROLE_USER)
    last_login = models.DateTimeField(null=True, blank=True)  # Add this
    is_active = models.BooleanField(default=True)  # Add this if missing
    

    def __str__(self):
        return self.email


class DeliveryPartner(models.Model):
    VEHICLE_BIKE = 'bike'
    VEHICLE_SCOOTER = 'scooter'
    VEHICLE_CAR = 'car'
    VEHICLE_CHOICES = [
        (VEHICLE_BIKE, 'Bike'),
        (VEHICLE_SCOOTER, 'Scooter'),
        (VEHICLE_CAR, 'Car'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='delivery_partner')
    profile = models.OneToOneField(Profile, on_delete=models.CASCADE, related_name='delivery_partner')
    phone = models.CharField(max_length=10)
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_CHOICES)
    is_approved = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.profile.name} ({self.get_vehicle_type_display()})"
    
    
class Product(models.Model):
    UNIT_KG = "kg"
    UNIT_PLATE = "plate"
    UNIT_PIECE = "piece"
    UNIT_SCOOP = "scoop"
    UNIT_PACKET = "packet"
    UNIT_CUP = "cup"
    UNIT_CAN = "can"
    UNIT_CHOICES = [
        (UNIT_KG, "Kilogram"),
        (UNIT_PLATE, "Plate"),
        (UNIT_PIECE, "Piece"),
        (UNIT_SCOOP, "Scoop"),
        (UNIT_PACKET, "Packet"),
        (UNIT_CUP, "Cup"),
        (UNIT_CAN, "Can"),
    ]
    CATEGORY_CHOICES=[
        ('Fast Food','Fast Food'),
        ('Combo Meal','Combo Meal'),
        ('Punjabi Delights','Punjabi Delights'),
        ('South Indian','South Indian'),
        ('Desserts','Desserts'),
        ('Beverages','Beverages'),
    ]
    name = models.CharField(max_length=100)
    image = models.ImageField(upload_to='products/')
    description = models.TextField(blank=True)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    unit = models.CharField(max_length=10, choices=UNIT_CHOICES, default=UNIT_PIECE)
    min_quantity = models.FloatField(default=1)
    category = models.CharField(max_length=50, choices=CATEGORY_CHOICES, default='Fast Food')
    is_available = models.BooleanField(default=True)
    discount_percent = models.PositiveIntegerField(default=0) 
    storage_instructions = models.CharField(max_length=255, blank=True, null=True)

    def __str__(self):
        return self.name

    @property
    def discounted_price(self):
        if self.discount_percent > 0:
            return self.price - (self.price * self.discount_percent / 100)
        return self.price

    @property
    def allows_decimal_quantity(self):
        return self.unit == self.UNIT_KG

    @property
    def normalized_min_quantity(self):
        return self.min_quantity if self.allows_decimal_quantity else max(1, int(self.min_quantity))

    def clean(self):
        if self.min_quantity <= 0:
            raise ValidationError({"min_quantity": "Minimum quantity must be greater than zero."})
        if not self.allows_decimal_quantity and self.min_quantity != int(self.min_quantity):
            raise ValidationError({"min_quantity": "Non-kg products must use whole-number minimum quantities."})
    
    
class Order(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)
    assigned_delivery_partner = models.ForeignKey(
        'DeliveryPartner',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_orders',
    )
    order_date = models.DateTimeField(auto_now_add=True)
    delivery_date = models.DateField(null=True, blank=True)  # user selects
    total_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    status = models.CharField(max_length=20, choices=[
        ('Pending', 'Pending'),
        ('Confirmed', 'Confirmed'),
        ('Delivered', 'Delivered'),
        ('Cancelled', 'Cancelled')
    ], default='Pending')
    flat = models.CharField(max_length=100)
    street = models.CharField(max_length=100)
    city = models.CharField(max_length=50)
    pincode = models.CharField(max_length=6)
    PAYMENT_CHOICES = [
    ('COD', 'Cash on Delivery'),
    ('UPI', 'UPI'),
    ('Card', 'Card'),
    ]

    payment_method = models.CharField(max_length=20, choices=PAYMENT_CHOICES)

    def __str__(self):
        return f"Order #{self.id} - {self.profile.name}"

    @property
    def grand_total(self):
        return self.total_amount or sum(item.total_price for item in self.items.all())
    
class Card(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)  # link to user
    card_name = models.CharField(max_length=100)  # Card holder name
    card_number_last4 = models.CharField(max_length=4)  # Only last 4 digits
    expiry = models.CharField(max_length=5)  # MM-YY format
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.card_name} ****{self.card_number_last4}"

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='items')
    product = models.ForeignKey(Product, on_delete=models.SET_NULL, null=True, blank=True)

    product_name = models.CharField(max_length=100)
    category = models.CharField(max_length=50)
    unit = models.CharField(max_length=10, choices=Product.UNIT_CHOICES, default=Product.UNIT_PIECE)
    price = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.FloatField(default=1)

    @property
    def total_price(self):
        return self.price * Decimal(str(self.quantity))

    def __str__(self):
        return f"{self.product_name} ({self.quantity} {self.unit})"
    
    
class Cart(models.Model):
    profile = models.ForeignKey(Profile, on_delete=models.CASCADE)  # instead of User
    product = models.ForeignKey(Product, on_delete=models.CASCADE)

    # Snapshot fields (auto filled from Product)
    product_name = models.CharField(max_length=100)
    category = models.CharField(max_length=50)
    unit = models.CharField(max_length=10, choices=Product.UNIT_CHOICES, default=Product.UNIT_PIECE)
    price_at_time = models.DecimalField(max_digits=10, decimal_places=2)

    quantity = models.FloatField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    @property
    def total_price(self):
        return self.price_at_time * Decimal(str(self.quantity))

    def save(self, *args, **kwargs):
        # Auto-fill snapshot fields only when new cart item is created
        if not self.pk:  
            self.product_name = self.product.name
            self.category = self.product.category
            self.unit = self.product.unit
            self.price_at_time = self.product.discounted_price
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.profile.email} - {self.product_name} ({self.quantity} {self.unit})"


class Review(models.Model):
    client_name = models.CharField(max_length=100)
    profession = models.CharField(max_length=100)
    review = models.TextField()
    image = models.ImageField(upload_to='review/', default='default-user.png')
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.client_name


# order=payment
# card=card_details
    
