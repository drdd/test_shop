from django.shortcuts import render, get_object_or_404, redirect
from .models import Product, Category
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from django.views import View
from django.contrib.auth import logout
from django.views.decorators.http import require_POST
from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django_ratelimit.decorators import ratelimit
from django.utils.decorators import method_decorator


@ratelimit(key='ip', rate='30/m', block=True)
def product_list(request):
    # Входные параметры и базовая валидация
    raw_query = request.GET.get('q', '')
    query = raw_query.strip()[:200]  # обрезаем длину запроса, предотвращаем DoS через очень длинные строки

    # Валидируем category_id как целое число; невалидное значение игнорируем
    category_id = request.GET.get('category')
    try:
        category_id = int(category_id) if category_id is not None and category_id != '' else None
    except (ValueError, TypeError):
        category_id = None

    # Пагинация: валидируем страницу и ограничиваем per_page
    try:
        page = int(request.GET.get('page', 1))
    except (ValueError, TypeError):
        page = 1
    per_page = 8
    per_page = max(1, min(per_page, 100))  # защитный ограничитель на per_page (если динамически меняется)

    # Строим фильтр через Q — безопасно для ORM
    filters = Q()
    if category_id:
        filters &= Q(category_id=category_id)
    if query:
        filters &= Q(name__icontains=query) | Q(description__icontains=query)

    # Базовый queryset — используем select_related для оптимизации
    qs = Product.objects.filter(filters).select_related('category')

    # Paginator заботится о корректной работе с offset/limit и защищает от огромных офсетов
    paginator = Paginator(qs, per_page)
    try:
        products_page = paginator.page(page)
    except PageNotAnInteger:
        products_page = paginator.page(1)
    except EmptyPage:
        products_page = paginator.page(paginator.num_pages)

    categories = Category.objects.all()

    return render(request, 'product_list.html', {
        'products': products_page.object_list,
        'page_obj': products_page,
        'paginator': paginator,
        'categories': categories,
        'selected_category': category_id,
        'query': query,
    })


@ratelimit(key='ip', rate='30/m', block=True)
def product_detail(request, pk):
    product = get_object_or_404(Product, pk=pk)
    return render(request, 'product_detail.html', {'product': product})


@require_POST
@login_required(login_url='/login/')
@ratelimit(key='ip', rate='30/m', block=True)
def cart_add(request, product_id):
    cart = request.session.get('cart', {})
    product = get_object_or_404(Product, id=product_id)
    if str(product_id) in cart:
        cart[str(product_id)] += 1
    else:
        cart[str(product_id)] = 1

    request.session['cart'] = cart
    request.session.modified = True
    return redirect('cart_detail')


@require_POST
@login_required(login_url='/login/')
@ratelimit(key='ip', rate='30/m', block=True)
def cart_update_all(request):
    cart = request.session.get('cart', {})
    action = request.POST.get('action')

    if action == 'update':
        updated_cart = {}
        for key, value in request.POST.items():
            if key.startswith('quantity_'):
                try:
                    product_id = key.split('_')[1]
                    quantity = int(value)
                    if quantity > 0:
                        updated_cart[product_id] = quantity
                except (IndexError, ValueError):
                    continue
        request.session['cart'] = updated_cart

    elif action and action.startswith('remove_'):
        product_id = action.split('_')[1]
        cart.pop(product_id, None)
        request.session['cart'] = cart

    request.session.modified = True
    return redirect('cart_detail')


@login_required(login_url='/login/')
@ratelimit(key='ip', rate='30/m', block=True)
def cart_detail(request):
    from tshop.utils.cart import get_cart_items

    cart = request.session.get('cart', {})
    cart_items, cart_total = get_cart_items(cart)

    context = {
        'cart_items': cart_items,
        'cart_total': cart_total,
    }
    return render(request, 'cart.html', context)


@ratelimit(key='ip', rate='30/m', block=True)
def signup(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect('login')  # или 'product_list'
    else:
        form = UserCreationForm()
    return render(request, 'signup.html', {'form': form, 'header': True, 'site_name': 'Регистрация на Лаки и Краски'})


@method_decorator(login_required(login_url='/login/'), name='dispatch')
@method_decorator(ratelimit(key='ip', rate='30/m', block=True), name='dispatch')
class LogoutViewGetPost(View):
    def get(self, request):
        logout(request)
        return redirect('/')

    def post(self, request):
        logout(request)
        return redirect('/')