def site_info(request):
    return {"site_name": "Лаки и Краски"}


def cart_total_items(request):
    cart = request.session.get('cart', {})
    return {'cart_total_items': sum(cart.values())}
