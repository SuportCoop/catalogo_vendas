import urllib.parse
import urllib.request
import json
import logging
from django.urls import reverse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.models import User
from django.contrib.auth.forms import AuthenticationForm
from django.contrib.auth.decorators import login_required
from django.contrib.admin.views.decorators import staff_member_required
from django.http import JsonResponse, HttpResponseForbidden
from django.db.models import Sum, Count, Q, F
from django.utils import timezone
from datetime import date
from decimal import Decimal

from django.utils.text import slugify

from .models import Category, Product, ProductImage, Client, Purchase, PurchaseItem
from .forms import ProductForm, ClientForm, UserCreateForm, CheckoutForm, CategoryForm

# ==========================================
# CLIENTE / PÁGINAS PÚBLICAS
# ==========================================

def catalog(request):
    # Buscar apenas produtos ativos no catálogo
    products = Product.objects.filter(is_active=True).order_by('name')
    categories = Category.objects.all().order_by('name')
    
    # Filtro por categoria
    category_slug = request.GET.get('category')
    selected_category = None
    if category_slug:
        selected_category = get_object_or_404(Category, slug=category_slug)
        products = products.filter(category=selected_category)
        
    # Barra de pesquisa
    query = request.GET.get('q')
    if query:
        products = products.filter(
            Q(name__icontains=query) | Q(code__icontains=query) | Q(description__icontains=query)
        )
        
    # Carrinho na sessão para exibir quantidade rápida no header
    cart = request.session.get('cart', {})
    cart_count = sum(cart.values())
    
    context = {
        'products': products,
        'categories': categories,
        'selected_category': selected_category,
        'cart_count': cart_count,
        'q': query,
    }
    return render(request, 'catalogo/catalog.html', context)


def product_detail_json(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    images = [img.image.url for img in product.images.all()]
    # Se não houver imagens, adiciona um placeholder
    if not images:
        images = ['/static/images/placeholder.png']
    
    return JsonResponse({
        'id': product.id,
        'code': product.code,
        'name': product.name,
        'sale_price': float(product.sale_price),
        'stock': product.stock,
        'description': product.description,
        'category': product.category.name,
        'images': images
    })


def cart_view(request):
    cart = request.session.get('cart', {})
    cart_items = []
    total = 0
    
    for prod_id, qty in cart.items():
        try:
            product = Product.objects.get(id=prod_id, is_active=True)
            subtotal = product.sale_price * qty
            total += subtotal
            cart_items.append({
                'product': product,
                'quantity': qty,
                'subtotal': subtotal
            })
        except Product.DoesNotExist:
            # Produto inativado ou removido
            pass
            
    # Formulário de identificação do cliente
    client_data = None
    if request.user.is_authenticated:
        try:
            client_data = Client.objects.get(user=request.user)
        except Client.DoesNotExist:
            pass
            
    # Inicializa o form com dados se já logado
    form = CheckoutForm(instance=client_data)
    
    context = {
        'cart_items': cart_items,
        'total': total,
        'form': form,
        'is_logged_in': request.user.is_authenticated
    }
    return render(request, 'catalogo/cart.html', context)


def cart_add(request, product_id):
    product = get_object_or_404(Product, id=product_id, is_active=True)
    cart = request.session.get('cart', {})
    
    # Incrementa
    cart[str(product_id)] = cart.get(str(product_id), 0) + 1
    request.session['cart'] = cart
    messages.success(request, f"{product.name} adicionado ao carrinho.")
    
    return redirect('catalog')


def cart_remove(request, product_id):
    cart = request.session.get('cart', {})
    if str(product_id) in cart:
        del cart[str(product_id)]
        request.session['cart'] = cart
        messages.success(request, "Produto removido do carrinho.")
    return redirect('cart_view')


def cart_update(request):
    if request.method == 'POST':
        cart = request.session.get('cart', {})
        for key, value in request.POST.items():
            if key.startswith('quantity_'):
                prod_id = key.split('_')[1]
                try:
                    qty = int(value)
                    if qty > 0:
                        cart[prod_id] = qty
                    else:
                        if prod_id in cart:
                            del cart[prod_id]
                except ValueError:
                    pass
        request.session['cart'] = cart
        request.session.modified = True
        messages.success(request, "Carrinho atualizado.")
    return redirect('cart_view')


def checkout(request):
    if request.method != 'POST':
        return redirect('cart_view')
        
    cart = request.session.get('cart', {})
    if not cart:
        messages.error(request, "Seu carrinho está vazio.")
        return redirect('catalog')
        
    # Verificar se as informações do formulário são válidas
    form = CheckoutForm(request.POST)
    client = None
    
    if request.user.is_authenticated:
        # Se logado, recupera ou atualiza o perfil do cliente
        try:
            client = Client.objects.get(user=request.user)
            form = CheckoutForm(request.POST, instance=client)
        except Client.DoesNotExist:
            client = None
            
    if form.is_valid():
        client = form.save(commit=False)
        if request.user.is_authenticated:
            client.user = request.user
        client.save()
    else:
        # Se dados inválidos, re-renderiza o carrinho com erros
        cart_items = []
        total = 0
        for prod_id, qty in cart.items():
            product = get_object_or_404(Product, id=prod_id)
            subtotal = product.sale_price * qty
            total += subtotal
            cart_items.append({'product': product, 'quantity': qty, 'subtotal': subtotal})
        return render(request, 'catalogo/cart.html', {
            'cart_items': cart_items,
            'total': total,
            'form': form,
            'is_logged_in': request.user.is_authenticated
        })

    # Criar a compra
    total_value = 0
    # Primeiro calcula o total e verifica estoque
    items_to_create = []
    for prod_id, qty in cart.items():
        product = get_object_or_404(Product, id=prod_id)
        subtotal = product.sale_price * qty
        total_value += subtotal
        items_to_create.append((product, qty, product.sale_price))
        
    # Criar registro
    purchase = Purchase.objects.create(
        client=client,
        total_value=total_value,
        status='Pendente',
        payment_method='PIX'
    )
    
    # Criar itens e abater estoque
    for product, qty, price in items_to_create:
        PurchaseItem.objects.create(
            purchase=purchase,
            product=product,
            quantity=qty,
            price=price
        )
        product.stock = max(0, product.stock - qty)
        product.save()
        
    # Esvaziar carrinho
    request.session['cart'] = {}
    request.session.modified = True
    
    # Gerar link de pagamento InfinitePay
    logger = logging.getLogger(__name__)
    items_payload = []
    for item in purchase.items.all():
        items_payload.append({
            "quantity": item.quantity,
            "price": int(item.price * 100),  # em centavos
            "description": item.product.name
        })

    payload = {
        "handle": "caio-c_farias",
        "items": items_payload,
        "order_nsu": str(purchase.id),
        "redirect_url": request.build_absolute_uri(reverse('purchase_history'))
    }

    checkout_url = None
    try:
        req = urllib.request.Request(
            "https://api.checkout.infinitepay.io/links",
            data=json.dumps(payload).encode('utf-8'),
            headers={
                'Content-Type': 'application/json',
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            },
            method='POST'
        )
        with urllib.request.urlopen(req, timeout=5) as response:
            res_data = json.loads(response.read().decode('utf-8'))
            checkout_url = res_data.get("url")
            if checkout_url:
                purchase.payment_link = checkout_url
                purchase.save()
    except Exception as e:
        logger.error(f"Erro ao gerar link de pagamento no InfinitePay: {e}")
        checkout_url = None

    # Gerar link do WhatsApp
    whatsapp_number = "5511971498691"
    msg = f"Olá! Gostaria de finalizar minha compra.\n\n"
    msg += f"*Pedido #{purchase.id}*\n"
    msg += f"*Cliente:* {client.name}\n"
    if client.cpf_cnpj:
        msg += f"*CPF/CNPJ:* {client.cpf_cnpj}\n"
    msg += f"*Contato:* {client.contact}\n"
    if client.address:
        msg += f"*Endereço:* {client.address}\n"
    msg += "\n*Produtos comprados:*\n"
    for item in purchase.items.all():
        msg += f"- {item.quantity}x {item.product.name} (Cód: {item.product.code}) - R$ {item.price:.2f} un.\n"
    msg += f"\n*Valor Total:* R$ {purchase.total_value:.2f}\n\n"
    
    if purchase.payment_link:
        msg += f"*Link de Pagamento (Cartão/Pix):* {purchase.payment_link}\n\n"
    else:
        msg += f"*Pagamento via PIX* chave celular: 11 971498691\n"
        
    msg += f"Por favor, confirme meu pedido. Estou enviando o comprovante em seguida."
    
    encoded_msg = urllib.parse.quote(msg)
    whatsapp_url = f"https://api.whatsapp.com/send?phone={whatsapp_number}&text={encoded_msg}"
    
    return render(request, 'catalogo/checkout_success.html', {
        'purchase': purchase,
        'whatsapp_url': whatsapp_url,
        'pix_key': "11 971498691",
        'checkout_url': checkout_url
    })


@login_required
def purchase_history(request):
    try:
        client = Client.objects.get(user=request.user)
        purchases = Purchase.objects.filter(client=client).order_by('-date')
    except Client.DoesNotExist:
        purchases = []
        
    return render(request, 'catalogo/history.html', {'purchases': purchases})


# ==========================================
# AUTENTICAÇÃO E CADASTROS PÚBLICOS
# ==========================================

def client_register(request):
    if request.method == 'POST':
        user_form = UserCreateForm(request.POST)
        client_form = ClientForm(request.POST)
        if user_form.is_valid() and client_form.is_valid():
            user = user_form.save()
            client = client_form.save(commit=False)
            client.user = user
            client.save()
            
            login(request, user)
            messages.success(request, "Cadastro realizado com sucesso!")
            return redirect('catalog')
    else:
        user_form = UserCreateForm()
        client_form = ClientForm()
        
    return render(request, 'catalogo/register.html', {
        'user_form': user_form,
        'client_form': client_form
    })


def client_login(request):
    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None:
                login(request, user)
                messages.success(request, f"Bem-vindo, {username}!")
                if user.is_staff:
                    return redirect('admin_dashboard')
                return redirect('catalog')
        else:
            messages.error(request, "Usuário ou senha incorretos.")
    else:
        form = AuthenticationForm()
    return render(request, 'catalogo/login.html', {'form': form})


def client_logout(request):
    logout(request)
    messages.success(request, "Sessão encerrada com sucesso.")
    return redirect('catalog')


# ==========================================
# DASHBOARD ADMINISTRATIVO & FINANCEIRO (Protegidos)
# ==========================================

@staff_member_required
def admin_dashboard(request):
    # Data de hoje
    today_date = timezone.localdate()

    # Métricas Globais/Período
    # 1. Quanto tenho pra receber do ano corrente (todas as compras não pagas e não canceladas do ano atual)
    to_receive_purchases = Purchase.objects.filter(is_paid=False).exclude(status='Cancelada').filter(date__year=today_date.year)
    total_to_receive = to_receive_purchases.aggregate(total=Sum('total_value'))['total'] or Decimal('0.00')
    to_receive_list = to_receive_purchases.order_by('due_date', '-date')

    # 2. Quanto foi vendido no mês corrente (exclui canceladas)
    sales_month_query = Purchase.objects.exclude(status='Cancelada').filter(date__year=today_date.year, date__month=today_date.month)
    total_sold_period = sales_month_query.aggregate(total=Sum('total_value'))['total'] or Decimal('0.00')

    # 3. Quanto foi recebido no mês corrente (compras pagas, exclui canceladas)
    received_month_query = Purchase.objects.filter(is_paid=True).exclude(status='Cancelada').filter(date__year=today_date.year, date__month=today_date.month)
    total_received_period = received_month_query.aggregate(total=Sum('total_value'))['total'] or Decimal('0.00')

    # Outras métricas auxiliares para o mês corrente
    total_qty_sold = PurchaseItem.objects.filter(purchase__in=sales_month_query).aggregate(total=Sum('quantity'))['total'] or 0
    top_client = sales_month_query.values('client__name').annotate(total_spent=Sum('total_value')).order_by('-total_spent').first()

    # Últimos 5 pedidos recentes no sistema
    recent_purchases = Purchase.objects.all().order_by('-date')[:5]

    context = {
        'today': today_date,
        'total_to_receive': total_to_receive,
        'to_receive_list': to_receive_list,
        'total_sold_period': total_sold_period,
        'total_received_period': total_received_period,
        'total_qty_sold': total_qty_sold,
        'top_client': top_client,
        'recent_purchases': recent_purchases,
    }
    return render(request, 'catalogo/admin_dashboard.html', context)


@staff_member_required
def admin_purchases_list(request):
    today_date = timezone.localdate()
    
    # Obter parâmetros de filtro
    year_param = request.GET.get('year')
    month_param = request.GET.get('month')
    day_param = request.GET.get('day')
    product_param = request.GET.get('product')
    is_filtered = request.GET.get('filter_active') == '1'
    
    # Padrão: ano e mês atuais (se não for filtrado)
    if not is_filtered:
        filter_year = today_date.year
        filter_month = today_date.month
        filter_day = None
        filter_product = None
    else:
        filter_year = int(year_param) if year_param else None
        filter_month = int(month_param) if month_param else None
        filter_day = int(day_param) if day_param else None
        filter_product = int(product_param) if product_param else None

    # Filtrar compras para a listagem principal
    purchases_query = Purchase.objects.all()
    if filter_year:
        purchases_query = purchases_query.filter(date__year=filter_year)
    if filter_month:
        purchases_query = purchases_query.filter(date__month=filter_month)
    if filter_day:
        purchases_query = purchases_query.filter(date__day=filter_day)
    if filter_product:
        purchases_query = purchases_query.filter(items__product_id=filter_product).distinct()
        
    purchases = purchases_query.order_by('-date')

    # Anos disponíveis para o seletor do filtro
    years_dates = list(Purchase.objects.dates('date', 'year'))
    available_years = [y.year for y in years_dates]
    if today_date.year not in available_years:
        available_years.append(today_date.year)
    available_years = sorted(list(set(available_years)), reverse=True)

    months_list = [
        (1, 'Janeiro'), (2, 'Fevereiro'), (3, 'Março'), (4, 'Abril'),
        (5, 'Maio'), (6, 'Junho'), (7, 'Julho'), (8, 'Agosto'),
        (9, 'Setembro'), (10, 'Outubro'), (11, 'Novembro'), (12, 'Dezembro')
    ]
    
    all_products = Product.objects.all().order_by('name')

    context = {
        'purchases': purchases,
        'today': today_date,
        'filter_year': filter_year,
        'filter_month': filter_month,
        'filter_day': filter_day,
        'filter_product': filter_product,
        'available_years': available_years,
        'months_list': months_list,
        'is_filtered': is_filtered,
        'all_products': all_products,
    }
    return render(request, 'catalogo/admin_purchases_list.html', context)


@staff_member_required
def update_purchase_status(request, purchase_id):
    if request.method == 'POST':
        purchase = get_object_or_404(Purchase, id=purchase_id)
        new_status = request.POST.get('status')
        
        # Apenas superadministradores podem alterar após finalizado
        if purchase.status == 'Finalizada' and not request.user.is_superuser:
            messages.error(request, "Apenas superadministradores podem alterar o status de um pedido já Finalizado.")
            return redirect('admin_dashboard')
            
        if new_status in dict(Purchase.STATUS_CHOICES):
            # Se for cancelada e estava finalizada ou pendente, devolver o estoque
            if new_status == 'Cancelada' and purchase.status != 'Cancelada':
                for item in purchase.items.all():
                    item.product.stock += item.quantity
                    item.product.save()
            # Se for mudada de Cancelada para outra, abater estoque se disponível
            elif purchase.status == 'Cancelada' and new_status != 'Cancelada':
                for item in purchase.items.all():
                    item.product.stock = max(0, item.product.stock - item.quantity)
                    item.product.save()
                    
            purchase.status = new_status
            if new_status == 'Finalizada':
                purchase.is_paid = True
            elif new_status == 'Cancelada' or new_status == 'Pendente':
                purchase.is_paid = False
            purchase.save()
            messages.success(request, f"Status da compra #{purchase.id} atualizado para {new_status}.")
    next_url = request.GET.get('next', 'admin_dashboard')
    if next_url not in ['admin_dashboard', 'admin_purchases_list']:
        next_url = 'admin_dashboard'
    return redirect(next_url)


@staff_member_required
def admin_products(request):
    products = Product.objects.all().order_by('name')
    return render(request, 'catalogo/admin_products.html', {'products': products})


@staff_member_required
def admin_product_create(request):
    if request.method == 'POST':
        form = ProductForm(request.POST)
        if form.is_valid():
            product = form.save()
            
            # Tratar upload de até 6 imagens
            files = request.FILES.getlist('images')
            count = 0
            for f in files:
                if count >= 6:
                    break
                ProductImage.objects.create(product=product, image=f)
                count += 1
                
            messages.success(request, "Produto cadastrado com sucesso!")
            return redirect('admin_products')
    else:
        form = ProductForm()
    return render(request, 'catalogo/admin_product_form.html', {'form': form, 'title': 'Cadastrar Produto'})


@staff_member_required
def admin_product_edit(request):
    pass # Seria implementada a view de edição. Vamos fazer completa:

@staff_member_required
def admin_product_edit(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    if request.method == 'POST':
        form = ProductForm(request.POST, instance=product)
        if form.is_valid():
            form.save()
            
            # Remover imagens marcadas para exclusão
            delete_images = request.POST.getlist('delete_images')
            for img_id in delete_images:
                ProductImage.objects.filter(id=img_id, product=product).delete()
                
            # Adicionar novas imagens se não exceder 6
            existing_count = product.images.count()
            files = request.FILES.getlist('images')
            for f in files:
                if existing_count >= 6:
                    break
                ProductImage.objects.create(product=product, image=f)
                existing_count += 1
                
            messages.success(request, "Produto atualizado com sucesso!")
            return redirect('admin_products')
    else:
        form = ProductForm(instance=product)
        
    return render(request, 'catalogo/admin_product_form.html', {
        'form': form,
        'product': product,
        'title': 'Editar Produto'
    })


@staff_member_required
def toggle_product_status(request, product_id):
    product = get_object_or_404(Product, id=product_id)
    product.is_active = not product.is_active
    product.save()
    status_str = "ativado" if product.is_active else "inativado"
    messages.success(request, f"Produto {product.name} {status_str} com sucesso.")
    return redirect('admin_products')


@staff_member_required
def admin_clients(request):
    clients = Client.objects.all().order_by('name')
    return render(request, 'catalogo/admin_clients.html', {'clients': clients})


@staff_member_required
def admin_client_create(request):
    if request.method == 'POST':
        form = ClientForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Cliente cadastrado com sucesso!")
            return redirect('admin_clients')
    else:
        form = ClientForm()
    return render(request, 'catalogo/admin_client_form.html', {'form': form, 'title': 'Cadastrar Cliente'})


@staff_member_required
def admin_client_edit(request, client_id):
    client = get_object_or_404(Client, id=client_id)
    if request.method == 'POST':
        form = ClientForm(request.POST, instance=client)
        if form.is_valid():
            form.save()
            messages.success(request, "Cliente atualizado com sucesso!")
            return redirect('admin_clients')
    else:
        form = ClientForm(instance=client)
    return render(request, 'catalogo/admin_client_form.html', {
        'form': form,
        'client': client,
        'title': 'Editar Cliente'
    })


@staff_member_required
def admin_users(request):
    users = User.objects.all().order_by('username')
    return render(request, 'catalogo/admin_users.html', {'users': users})


@staff_member_required
def admin_user_create(request):
    if request.method == 'POST':
        form = UserCreateForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, f"Usuário {user.username} cadastrado com sucesso!")
            return redirect('admin_users')
    else:
        form = UserCreateForm()
    return render(request, 'catalogo/admin_user_form.html', {'form': form})


@staff_member_required
def admin_user_toggle_staff(request, user_id):
    user = get_object_or_404(User, id=user_id)
    if user == request.user:
        messages.error(request, "Você não pode revogar seu próprio acesso administrativo!")
    else:
        user.is_staff = not user.is_staff
        user.save()
        status_str = "adicionado como Administrador" if user.is_staff else "removido de Administrador"
        messages.success(request, f"Acesso do usuário {user.username} {status_str}.")
    return redirect('admin_users')


@staff_member_required
def admin_categories(request):
    if request.method == 'POST':
        form = CategoryForm(request.POST)
        if form.is_valid():
            category = form.save(commit=False)
            category.slug = slugify(category.name)
            category.save()
            messages.success(request, f"Categoria '{category.name}' cadastrada com sucesso!")
            return redirect('admin_categories')
    else:
        form = CategoryForm()
    categories = Category.objects.all().order_by('name')
    return render(request, 'catalogo/admin_categories.html', {
        'form': form,
        'categories': categories
    })


from decimal import Decimal

@staff_member_required
def admin_client_portfolio(request):
    clients = Client.objects.all().order_by('name')
    portfolio = []
    
    for client in clients:
        purchases = Purchase.objects.filter(client=client)
        purchases_count = purchases.count()
        total_spent = purchases.filter(status='Finalizada').aggregate(total=Sum('total_value'))['total'] or Decimal('0.00')
        last_purchase = purchases.order_by('-date').first()
        last_purchase_date = last_purchase.date if last_purchase else None
        
        portfolio.append({
            'client': client,
            'purchases_count': purchases_count,
            'total_spent': total_spent,
            'last_purchase_date': last_purchase_date
        })
        
    # Sort portfolio by total_spent descending (best customer first)
    portfolio.sort(key=lambda x: x['total_spent'], reverse=True)
    
    return render(request, 'catalogo/admin_client_portfolio.html', {
        'portfolio': portfolio
    })


@staff_member_required
def admin_purchase_create(request):
    if request.method == 'POST':
        client_id = request.POST.get('client_id')
        discount_val = Decimal(request.POST.get('discount') or '0.00')
        payment_method = request.POST.get('payment_method', 'PIX')
        is_paid = request.POST.get('is_paid') == 'on'
        due_date_str = request.POST.get('due_date')
        
        due_date = None
        if due_date_str:
            try:
                due_date = date.fromisoformat(due_date_str)
            except ValueError:
                pass
                
        client = get_object_or_404(Client, id=client_id)
        
        # Read items
        product_ids = request.POST.getlist('product')
        quantities = request.POST.getlist('quantity')
        prices = request.POST.getlist('price')
        
        # We need to compute total value
        total_value = Decimal('0.00')
        items_to_create = []
        
        for p_id, qty_str, price_str in zip(product_ids, quantities, prices):
            try:
                qty = int(qty_str)
                price = Decimal(price_str)
                if qty > 0:
                    product = Product.objects.get(id=p_id)
                    total_value += price * qty
                    items_to_create.append((product, qty, price))
            except (Product.DoesNotExist, ValueError, TypeError):
                pass
                
        # Apply discount
        total_value = max(Decimal('0.00'), total_value - discount_val)
        
        if not items_to_create:
            messages.error(request, "Adicione pelo menos um produto com quantidade maior que zero.")
            clients = Client.objects.all().order_by('name')
            products = Product.objects.filter(is_active=True).order_by('name')
            return render(request, 'catalogo/admin_purchase_form.html', {
                'clients': clients,
                'products': products,
            })
            
        # Create Purchase
        purchase = Purchase.objects.create(
            client=client,
            total_value=total_value,
            discount=discount_val,
            due_date=due_date,
            is_paid=is_paid,
            status='Finalizada' if is_paid else 'Pendente',
            payment_method=payment_method
        )
        
        # Create PurchaseItems and update stock
        for product, qty, price in items_to_create:
            PurchaseItem.objects.create(
                purchase=purchase,
                product=product,
                quantity=qty,
                price=price
            )
            product.stock = max(0, product.stock - qty)
            product.save()
            
        messages.success(request, f"Venda manual #{purchase.id} registrada com sucesso.")
        return redirect('admin_dashboard')
        
    # GET method
    clients = Client.objects.all().order_by('name')
    products = Product.objects.filter(is_active=True).order_by('name')
    return render(request, 'catalogo/admin_purchase_form.html', {
        'clients': clients,
        'products': products,
    })


@staff_member_required
def admin_purchase_edit(request, purchase_id):
    purchase = get_object_or_404(Purchase, id=purchase_id)
    
    if request.method == 'POST':
        client_id = request.POST.get('client_id')
        discount_val = Decimal(request.POST.get('discount') or '0.00')
        payment_method = request.POST.get('payment_method', 'PIX')
        is_paid = request.POST.get('is_paid') == 'on'
        due_date_str = request.POST.get('due_date')
        
        due_date = None
        if due_date_str:
            try:
                due_date = date.fromisoformat(due_date_str)
            except ValueError:
                pass
                
        client = get_object_or_404(Client, id=client_id)
        
        # Read items
        product_ids = request.POST.getlist('product')
        quantities = request.POST.getlist('quantity')
        prices = request.POST.getlist('price')
        
        # We need to compute total value and validate items
        items_to_create = []
        for p_id, qty_str, price_str in zip(product_ids, quantities, prices):
            try:
                qty = int(qty_str)
                price = Decimal(price_str)
                if qty > 0:
                    product = Product.objects.get(id=p_id)
                    items_to_create.append((product, qty, price))
            except (Product.DoesNotExist, ValueError, TypeError):
                pass
                
        if not items_to_create:
            messages.error(request, "Adicione pelo menos um produto com quantidade maior que zero.")
            clients = Client.objects.all().order_by('name')
            products = Product.objects.filter(is_active=True).order_by('name')
            return render(request, 'catalogo/admin_purchase_edit.html', {
                'purchase': purchase,
                'clients': clients,
                'products': products,
            })
            
        # Restore stock for the old items first
        for item in purchase.items.all():
            item.product.stock += item.quantity
            item.product.save()
            
        # Delete old items
        purchase.items.all().delete()
        
        # Create new items and deduct stock
        total_value = Decimal('0.00')
        for product, qty, price in items_to_create:
            product.refresh_from_db()
            PurchaseItem.objects.create(
                purchase=purchase,
                product=product,
                quantity=qty,
                price=price
            )
            product.stock = max(0, product.stock - qty)
            product.save()
            total_value += price * qty
            
        # Update Purchase fields
        purchase.client = client
        purchase.discount = discount_val
        purchase.due_date = due_date
        purchase.is_paid = is_paid
        purchase.status = 'Finalizada' if is_paid else 'Pendente'
        purchase.payment_method = payment_method
        purchase.total_value = max(Decimal('0.00'), total_value - discount_val)
        purchase.save()
        
        messages.success(request, f"Venda #{purchase.id} atualizada com sucesso.")
        return redirect('admin_purchases_list')
        
    # GET method
    clients = Client.objects.all().order_by('name')
    products = Product.objects.filter(is_active=True).order_by('name')
    return render(request, 'catalogo/admin_purchase_edit.html', {
        'purchase': purchase,
        'clients': clients,
        'products': products,
    })

