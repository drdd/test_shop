from tshop.models import Product


def get_cart_items(session_cart):
    items = []
    total = 0

    for product_id, quantity in session_cart.items():
        try:
            product = Product.objects.get(id=product_id)
            total_price = product.price * quantity
            items.append({
                'product': product,
                'quantity': quantity,
                'total_price': total_price
            })
            total += total_price
        except Product.DoesNotExist:
            continue

    return items, total