from decimal import Decimal, InvalidOperation

from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Count, Q
from django.http import HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode, urlsafe_base64_encode
from django.views.decorators.http import require_GET, require_http_methods, require_POST
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.platypus import Paragraph, SimpleDocTemplate, Table, TableStyle

from .models import Card, Cart, Contact, DeliveryPartner, Order, OrderItem, Product, Profile, Review
from .tokens import profile_token_generator


SHIPPING_CHARGE = Decimal("50.00")
MAX_ORDER_ITEM_QUANTITY = Decimal("1000")
BUDGET_FRIENDLY_LIMIT = Decimal("150.00")


def _current_profile(request):
    profile_id = request.session.get("user_id")
    if not profile_id:
        return None
    return Profile.objects.filter(id=profile_id).first()


def _sync_session(request, profile):
    request.session["user_id"] = profile.id
    request.session["user_name"] = profile.name
    request.session["user_role"] = profile.role


def _get_available_delivery_partner():
    return (
        DeliveryPartner.objects.filter(is_approved=True)
        .annotate(
            active_order_count=Count(
                "assigned_orders",
                filter=Q(assigned_orders__status="Pending"),
            )
        )
        .order_by("active_order_count", "created_at", "id")
        .first()
    )


def _get_checkout_cart_items(profile):
    return list(Cart.objects.filter(profile=profile).select_related("product"))


def _validate_checkout_cart_items(cart_items):
    if not cart_items:
        raise ValueError("Your cart is empty.")

    unavailable_items = [item.product_name for item in cart_items if not item.product or not item.product.is_available]
    if unavailable_items:
        raise ValueError(f"These items are unavailable: {', '.join(unavailable_items)}")


def _available_products_queryset():
    return Product.objects.filter(is_available=True).order_by("name")


def _get_viewed_product_ids(request):
    return request.session.get("viewed_product_ids", [])


def _remember_viewed_product(request, product_id):
    viewed_ids = [pid for pid in _get_viewed_product_ids(request) if pid != product_id]
    viewed_ids.insert(0, product_id)
    request.session["viewed_product_ids"] = viewed_ids[:8]


def _recommended_for_user(request, limit=3):
    products = list(_available_products_queryset())
    if not products:
        return []

    profile = _current_profile(request)
    ordered_categories = []
    if profile:
        ordered_categories = list(
            OrderItem.objects.filter(order__profile=profile)
            .order_by("-order__order_date")
            .values_list("category", flat=True)
        )

    recommended = []
    seen_ids = set()

    for category in ordered_categories:
        for product in products:
            if product.category == category and product.id not in seen_ids:
                recommended.append(product)
                seen_ids.add(product.id)
                if len(recommended) >= limit:
                    return recommended

    for viewed_id in _get_viewed_product_ids(request):
        for product in products:
            if product.id == viewed_id:
                continue
            if product.id not in seen_ids:
                recommended.append(product)
                seen_ids.add(product.id)
                if len(recommended) >= limit:
                    return recommended

    for product in products:
        if product.id not in seen_ids:
            recommended.append(product)
            seen_ids.add(product.id)
            if len(recommended) >= limit:
                break

    return recommended


def _budget_friendly_products(limit=3):
    budget_products = [
        product for product in _available_products_queryset()
        if product.discounted_price <= BUDGET_FRIENDLY_LIMIT
    ]
    budget_products.sort(key=lambda product: (product.discounted_price, product.name))
    return budget_products[:limit]


def _view_based_recommendations(request, current_product, limit=3):
    products = list(_available_products_queryset().exclude(id=current_product.id))
    if not products:
        return []

    viewed_ids = _get_viewed_product_ids(request)
    viewed_products = {product.id: product for product in Product.objects.filter(id__in=viewed_ids)}
    viewed_categories = [viewed_products[pid].category for pid in viewed_ids if pid in viewed_products]

    recommendations = []
    seen_ids = set()

    for category in [current_product.category] + viewed_categories:
        for product in products:
            if product.category == category and product.id not in seen_ids:
                recommendations.append(product)
                seen_ids.add(product.id)
                if len(recommendations) >= limit:
                    return recommendations

    for product in products:
        if product.id not in seen_ids:
            recommendations.append(product)
            seen_ids.add(product.id)
            if len(recommendations) >= limit:
                break

    return recommendations


def _create_order_from_cart(profile, request):
    cart_items = _get_checkout_cart_items(profile)
    _validate_checkout_cart_items(cart_items)

    subtotal = sum(item.total_price for item in cart_items)
    assigned_delivery_partner = _get_available_delivery_partner()

    order = Order.objects.create(
        profile=profile,
        assigned_delivery_partner=assigned_delivery_partner,
        delivery_date=None,
        total_amount=subtotal + SHIPPING_CHARGE,
        flat=request.POST.get("flat", "").strip(),
        street=request.POST.get("street", "").strip(),
        city=request.POST.get("city", "").strip(),
        pincode=request.POST.get("pincode", "").strip(),
        payment_method=request.POST.get("payment_method", "COD"),
    )

    for item in cart_items:
        OrderItem.objects.create(
            order=order,
            product=item.product,
            product_name=item.product_name,
            category=item.category,
            unit=item.unit,
            price=item.price_at_time,
            quantity=item.quantity,
        )

    return order, cart_items


def _parse_quantity_for_product(product, raw_quantity):
    raw_value = str(raw_quantity).strip()
    if not raw_value:
        raise ValueError("Quantity is required.")

    try:
        quantity_decimal = Decimal(raw_value)
    except InvalidOperation as exc:
        raise ValueError("Enter a valid quantity.") from exc

    if quantity_decimal <= 0:
        raise ValueError("Quantity must be greater than zero.")

    minimum_quantity = Decimal(str(product.normalized_min_quantity))
    if quantity_decimal < minimum_quantity:
        raise ValueError(f"Minimum quantity for this item is {product.normalized_min_quantity}.")
    if quantity_decimal > MAX_ORDER_ITEM_QUANTITY:
        raise ValueError(f"Maximum quantity per item is {int(MAX_ORDER_ITEM_QUANTITY)}.")

    if product.allows_decimal_quantity:
        return float(quantity_decimal)

    if quantity_decimal != quantity_decimal.to_integral_value():
        raise ValueError(f"{product.get_unit_display()} quantity must be a whole number.")

    return int(quantity_decimal)


def index(request):
    reviews = Review.objects.order_by("-created_at")[:10]
    return render(
        request,
        "index.html",
        {
            "reviews": reviews,
            "recommended_products": _recommended_for_user(request),
            "budget_products": _budget_friendly_products(),
        },
    )


def about(request):
    return render(request, "about.html")


def signup(request):
    return render(request, "signup.html")


@require_http_methods(["POST"])
def user_signup(request):
    data = request.POST
    name = data.get("name", "").strip()
    email = data.get("email", "").strip().lower()
    contact_number = data.get("contact_number", "").strip()
    password1 = data.get("password1", "")
    password2 = data.get("password2", "")
    role = data.get("role", Profile.ROLE_USER)
    vehicle_type = data.get("vehicle_type", "").strip()
    phone = data.get("phone", "").strip()

    if not all([name, email, contact_number, password1, password2]):
        return JsonResponse({"success": False, "message": "All required fields must be filled."}, status=400)
    if password1 != password2:
        return JsonResponse({"success": False, "message": "Passwords do not match."}, status=400)
    if Profile.objects.filter(email=email).exists() or User.objects.filter(username=email).exists():
        return JsonResponse({"success": False, "message": "An account with this email already exists."}, status=400)
    if role not in {Profile.ROLE_USER, Profile.ROLE_DELIVERY}:
        role = Profile.ROLE_USER
    if role == Profile.ROLE_DELIVERY and (not vehicle_type or not phone):
        return JsonResponse({"success": False, "message": "Delivery partner details are required."}, status=400)

    with transaction.atomic():
        user = User.objects.create_user(
            username=email,
            email=email,
            password=password1,
            first_name=name,
        )
        profile = Profile.objects.create(
            user=user,
            name=name,
            email=email,
            password=user.password,
            contact_number=contact_number,
            role=role,
        )
        if role == Profile.ROLE_DELIVERY:
            DeliveryPartner.objects.create(
                user=user,
                profile=profile,
                phone=phone,
                vehicle_type=vehicle_type,
                is_approved=False,
            )

    message = "Signup successful. You can log in now."
    if role == Profile.ROLE_DELIVERY:
        message = "Signup successful. Delivery partner access will start after admin approval."
    return JsonResponse({"success": True, "message": message, "redirect_url": reverse("login")})


@require_http_methods(["GET", "POST"])
def user_login(request):
    if request.method == "GET":
        return render(request, "login.html")

    email = request.POST.get("email", "").strip().lower()
    password = request.POST.get("password", "")
    profile = Profile.objects.filter(email=email, is_active=True).select_related("user").first()

    if not profile or not profile.user:
        return JsonResponse({"success": False, "message": "Invalid email or password."}, status=400)

    user = authenticate(request, username=profile.user.username, password=password)
    if user is None:
        return JsonResponse({"success": False, "message": "Invalid email or password."}, status=400)

    if profile.role == Profile.ROLE_DELIVERY:
        delivery_partner = DeliveryPartner.objects.filter(profile=profile).first()
        if not delivery_partner or not delivery_partner.is_approved:
            return JsonResponse(
                {"success": False, "message": "Your delivery partner account is still pending approval."},
                status=403,
            )

    login(request, user)
    profile.last_login = timezone.now()
    profile.save(update_fields=["last_login"])
    _sync_session(request, profile)

    redirect_url = reverse("delivery_dashboard") if profile.role == Profile.ROLE_DELIVERY else reverse("index")
    return JsonResponse({"success": True, "message": "Login successful.", "redirect_url": redirect_url})


def delivery_dashboard(request):
    profile = _current_profile(request)
    if not profile or profile.role != Profile.ROLE_DELIVERY:
        return redirect("login")
    delivery_partner = get_object_or_404(DeliveryPartner, profile=profile)
    assigned_orders = (
        Order.objects.filter(assigned_delivery_partner=delivery_partner)
        .select_related("profile", "assigned_delivery_partner__profile")
        .prefetch_related("items")
        .order_by("status", "-order_date")
    )
    return render(
        request,
        "delivery_dashboard.html",
        {
            "profile": profile,
            "delivery_partner": delivery_partner,
            "assigned_orders": assigned_orders,
            "pending_orders_count": assigned_orders.filter(status="Pending").count(),
        },
    )


def product_list(request):
    products = Product.objects.all().order_by("name")
    selected_category = request.GET.get("category", "").strip()
    search_query = request.GET.get("q", "").strip()

    if selected_category:
        products = products.filter(category=selected_category)
    if search_query:
        products = products.filter(name__icontains=search_query)

    return render(
        request,
        "product.html",
        {
            "products": products,
            "selected_category": selected_category,
            "search_query": search_query,
        },
    )


def View_Detail(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    _remember_viewed_product(request, product.id)
    return render(
        request,
        "view_details.html",
        {
            "product": product,
            "view_based_products": _view_based_recommendations(request, product),
        },
    )


def _require_profile_json(request):
    profile = _current_profile(request)
    if not profile:
        return None, JsonResponse({"success": False, "error": "Please log in first."}, status=401)
    return profile, None


def _add_product_to_cart(profile, product, quantity):
    cart_item, created = Cart.objects.get_or_create(
        profile=profile,
        product=product,
        defaults={"quantity": quantity},
    )
    if not created:
        updated_quantity = Decimal(str(cart_item.quantity)) + Decimal(str(quantity))
        if updated_quantity > MAX_ORDER_ITEM_QUANTITY:
            raise ValueError(f"Maximum quantity per item is {int(MAX_ORDER_ITEM_QUANTITY)}.")
        cart_item.quantity += quantity
        cart_item.unit = product.unit
        cart_item.price_at_time = product.discounted_price
        cart_item.save(update_fields=["quantity", "unit", "price_at_time"])
    return cart_item


@require_GET
def Add_Cart(request, id):
    profile, error_response = _require_profile_json(request)
    if error_response:
        return error_response

    product = get_object_or_404(Product, id=id)
    if not product.is_available:
        return JsonResponse({"success": False, "error": "This product is out of stock."}, status=400)

    try:
        _add_product_to_cart(profile, product, product.normalized_min_quantity)
    except ValueError as exc:
        return JsonResponse({"success": False, "error": str(exc)}, status=400)
    cart_count = Cart.objects.filter(profile=profile).count()
    return JsonResponse({"success": True, "cart_count": cart_count})


@require_POST
def Add_Cart_Redirect(request, product_id):
    profile = _current_profile(request)
    if not profile:
        return redirect("login")

    product = get_object_or_404(Product, id=product_id)
    if not product.is_available:
        messages.error(request, "This product is out of stock.")
        return redirect("View_Detail", product_id=product.id)

    try:
        quantity = _parse_quantity_for_product(product, request.POST.get("quantity", product.normalized_min_quantity))
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("View_Detail", product_id=product.id)

    try:
        _add_product_to_cart(profile, product, quantity)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("View_Detail", product_id=product.id)
    messages.success(request, "Product added to cart.")
    return redirect("cart")


@require_GET
def get_cart_count(request):
    profile = _current_profile(request)
    count = Cart.objects.filter(profile=profile).count() if profile else 0
    return JsonResponse({"cart_count": count})


def cart_view(request):
    profile = _current_profile(request)
    if not profile:
        return redirect("login")
    cart_items = Cart.objects.filter(profile=profile).select_related("product").order_by("-added_at")
    total_price = sum((item.total_price for item in cart_items), Decimal("0.00"))
    grand_total = total_price + SHIPPING_CHARGE
    return render(
        request,
        "add_to_cart.html",
        {"cart_items": cart_items, "total_price": total_price, "grand_total": grand_total},
    )


@require_POST
def update_cart(request, item_id):
    profile = _current_profile(request)
    if not profile:
        return redirect("login")
    cart_item = get_object_or_404(Cart, id=item_id, profile=profile)
    try:
        quantity = _parse_quantity_for_product(cart_item.product, request.POST.get("quantity", cart_item.quantity))
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("cart")

    cart_item.quantity = quantity
    cart_item.unit = cart_item.product.unit
    cart_item.price_at_time = cart_item.product.discounted_price
    cart_item.save(update_fields=["quantity", "unit", "price_at_time"])
    return redirect("cart")


def remove_from_cart(request, item_id):
    profile = _current_profile(request)
    if not profile:
        return redirect("login")
    cart_item = get_object_or_404(Cart, id=item_id, profile=profile)
    cart_item.delete()
    return redirect("cart")


def checkout(request):
    profile = _current_profile(request)
    if not profile:
        return redirect("login")
    cart_items = Cart.objects.filter(profile=profile).select_related("product")
    total_price = sum((item.total_price for item in cart_items), Decimal("0.00"))
    grand_total = total_price + SHIPPING_CHARGE
    return render(
        request,
        "checkout.html",
        {"cart_items": cart_items, "total_price": total_price, "grand_total": grand_total},
    )


@require_POST
def place_order(request):
    profile = _current_profile(request)
    if not profile:
        return redirect("login")

    cart_items = _get_checkout_cart_items(profile)
    try:
        _validate_checkout_cart_items(cart_items)
    except ValueError as exc:
        messages.error(request, str(exc))
        return redirect("cart")

    payment_method = request.POST.get("payment_method", "COD")

    with transaction.atomic():
        order, cart_items = _create_order_from_cart(profile, request)

        if payment_method == "Card":
            card_number = request.POST.get("card_number", "").strip()
            if len(card_number) >= 4:
                Card.objects.create(
                    profile=profile,
                    card_name=request.POST.get("card_name", "").strip(),
                    card_number_last4=card_number[-4:],
                    expiry=request.POST.get("expiry", "").strip(),
                )

        Cart.objects.filter(profile=profile).delete()

    return redirect("order_success", order_id=order.id)


def order_success(request, order_id):
    order = get_object_or_404(
        Order.objects.select_related("assigned_delivery_partner__profile"),
        id=order_id,
    )
    return render(request, "order_success.html", {"order": order, "payment_method": order.payment_method.lower()})


@require_POST
def mark_order_delivered(request, order_id):
    profile = _current_profile(request)
    if not profile or profile.role != Profile.ROLE_DELIVERY:
        return redirect("login")

    delivery_partner = get_object_or_404(DeliveryPartner, profile=profile)
    order = get_object_or_404(Order, id=order_id, assigned_delivery_partner=delivery_partner)

    if order.status != "Delivered":
        order.status = "Delivered"
        order.delivery_date = timezone.localdate()
        order.save(update_fields=["status", "delivery_date"])

    return redirect("delivery_dashboard")


@require_http_methods(["GET", "POST"])
def contact(request):
    context = {}
    if request.method == "POST":
        Contact.objects.create(
            name=request.POST.get("name", "").strip(),
            email=request.POST.get("email", "").strip(),
            subject=request.POST.get("subject", "").strip(),
            message=request.POST.get("message", "").strip(),
        )
        context["message"] = "Message sent successfully."
    return render(request, "contact.html", context)


def logout_view(request):
    logout(request)
    request.session.flush()
    return redirect("login")


@require_http_methods(["GET", "POST"])
def edit_profile(request):
    profile = _current_profile(request)
    if not profile:
        return redirect("login")

    if request.method == "POST":
        profile.name = request.POST.get("name", "").strip()
        profile.contact_number = request.POST.get("contact_number", "").strip()

        current_password = request.POST.get("current_password", "")
        new_password = request.POST.get("new_password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if any([current_password, new_password, confirm_password]):
            if not profile.user.check_password(current_password):
                messages.error(request, "Current password is incorrect.")
                return redirect("edit_profile")
            if new_password != confirm_password:
                messages.error(request, "New password and confirm password do not match.")
                return redirect("edit_profile")
            if new_password:
                profile.user.set_password(new_password)
                profile.user.save()
                profile.password = profile.user.password
                login(request, profile.user)

        profile.user.first_name = profile.name
        profile.user.email = profile.email
        profile.user.save()
        profile.save()
        _sync_session(request, profile)
        messages.success(request, "Profile updated successfully.")
        return redirect("edit_profile")

    return render(
        request,
        "edit_profile.html",
        {"name": profile.name, "contact_number": profile.contact_number},
    )


@require_http_methods(["GET", "POST"])
def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        profile = Profile.objects.filter(email=email).first()
        if not profile:
            messages.error(request, "No account found for that email address.")
            return render(request, "forgot_password.html", {"email": email, "error_type": "email"})

        uid = urlsafe_base64_encode(str(profile.pk).encode())
        token = profile_token_generator.make_token(profile)
        reset_link = request.build_absolute_uri(reverse("reset_password", args=[uid, token]))

        try:
            send_mail(
                "Reset your FoodZone password",
                f"Use this link to reset your password:\n\n{reset_link}",
                settings.DEFAULT_FROM_EMAIL,
                [profile.email],
                fail_silently=False,
            )
            messages.success(request, "Password reset link sent to your email.")
        except Exception:
            messages.error(request, "Unable to send reset email right now.")

    return render(request, "forgot_password.html")


@require_http_methods(["GET", "POST"])
def reset_password(request, uidb64, token):
    try:
        uid = force_str(urlsafe_base64_decode(uidb64))
        profile = Profile.objects.select_related("user").get(pk=uid)
    except Exception:
        profile = None

    if not profile or not profile_token_generator.check_token(profile, token):
        return render(request, "reset_password_invalid.html")

    if request.method == "POST":
        password = request.POST.get("password", "")
        confirm_password = request.POST.get("confirm_password", "")

        if password != confirm_password:
            messages.error(request, "Passwords do not match.")
            return render(request, "reset_password.html")

        profile.user.set_password(password)
        profile.user.save()
        profile.password = profile.user.password
        profile.save(update_fields=["password"])
        messages.success(request, "Password reset successful. Please log in.")
        return redirect("login")

    return render(request, "reset_password.html")


def payment_report(request):
    orders = Order.objects.select_related("profile").order_by("-order_date")

    response = HttpResponse(content_type="application/pdf")
    response["Content-Disposition"] = 'attachment; filename="payment_report.pdf"'

    doc = SimpleDocTemplate(response, pagesize=A4)
    styles = getSampleStyleSheet()
    elements = [
        Paragraph("<b>Payment Report</b>", styles["Title"]),
        Paragraph(timezone.now().strftime("Generated on %d-%m-%Y %H:%M"), styles["Normal"]),
    ]

    rows = [["User Name", "Payment Type", "Amount (Rs)", "City", "Pincode"]]
    for order in orders:
        rows.append([
            order.profile.name,
            order.payment_method,
            f"{order.total_amount}",
            order.city,
            order.pincode,
        ])

    table = Table(rows, colWidths=[130, 90, 90, 100, 80])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.lightgreen),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.8, colors.grey),
                ("BACKGROUND", (0, 1), (-1, -1), colors.whitesmoke),
            ]
        )
    )
    elements.append(table)
    doc.build(elements)
    return response


def my_order(request):
    profile = _current_profile(request)
    if not profile:
        return redirect("login")
    orders = (
        Order.objects.filter(profile=profile)
        .select_related("assigned_delivery_partner__profile")
        .prefetch_related("items")
        .order_by("-order_date")
    )
    return render(request, "my_order.html", {"orders": orders})
