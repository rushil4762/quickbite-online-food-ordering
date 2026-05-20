from django.contrib import admin
from myapp import views 
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static



urlpatterns = [
    #path('admin/', admin.site.urls),
    path('dashboard/secure/', admin.site.urls),
    path('',views.index,name="index"),  
    path('index.html',views.index,name="index"),
    path('login.html',views.user_login,name="login"),
    path('signup.html',views.signup,name="signup"),
    path('api/auth/signup/', views.user_signup, name='api_signup'),
    path('api/auth/login/', views.user_login, name='api_login'),
    path('delivery/dashboard/', views.delivery_dashboard, name='delivery_dashboard'),
    path('delivery/orders/<int:order_id>/deliver/', views.mark_order_delivered, name='mark_order_delivered'),
    path('about.html',views.about,name="about"),
    path('product.html',views.product_list,name="product"),
    path('product/<int:product_id>/', views.View_Detail, name='View_Detail'),
    path('add_cart/<int:id>/', views.Add_Cart, name='add_cart'),

    path('get_cart_count/', views.get_cart_count, name='get_cart_count'),

    path('cart/', views.cart_view, name="cart"),
    path('checkout/', views.checkout, name='checkout'),
    path('order-success/<int:order_id>/', views.order_success, name='order_success'),
    path('place_order/', views.place_order, name='place_order'),

    path('update_cart/<int:item_id>/', views.update_cart, name='update_cart'),
    path('remove_from_cart/<int:item_id>/', views.remove_from_cart, name='remove_from_cart'),
    # path('add-to-cart/<int:product_id>/', views.Add_Cart, name='Add_Cart'),
    

    path('contact.html',views.contact,name="contact"),
    path('logout/', views.logout_view, name='logout'),
    path('edit-profile/', views.edit_profile, name='edit_profile'),
    path('forgot-password/', views.forgot_password, name='forgot_password'),
    path('reset-password/<uidb64>/<token>/', views.reset_password, name='reset_password'),
    # path('add_cart/<int:id>/', views.add_cart, name='add_cart'),
    
    path('add_cart_redirect/<int:product_id>/', views.Add_Cart_Redirect, name='add_cart_redirect'),

    path("payment-report/", views.payment_report, name="payment_report"),
    path('my-orders/', views.my_order, name='my_orders'),

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
