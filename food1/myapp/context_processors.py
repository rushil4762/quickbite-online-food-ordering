from .models import Cart

def cart_count(request):
    user_id = request.session.get('user_id')
    count = 0
    if user_id:
        count = Cart.objects.filter(profile_id=user_id).count()
    return {'cart_count': count}
