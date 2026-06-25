from django.test import TestCase, Client as HttpClient
from django.contrib.auth.models import User
from django.utils import timezone
from decimal import Decimal
from datetime import date

from .models import Category, Product, Client, Purchase, PurchaseItem

class CatalogSystemTestCase(TestCase):
    def setUp(self):
        # 1. Criar Categorias
        self.category = Category.objects.create(name="Eletrônicos", slug="eletronicos")
        
        # 2. Criar Produtos
        self.product1 = Product.objects.create(
            code="E001",
            name="Smartphone X",
            cost_price=Decimal("1500.00"),
            sale_price=Decimal("2500.00"),
            category=self.category,
            stock=10,
            description="Smartphone de alta tecnologia"
        )
        self.product2 = Product.objects.create(
            code="E002",
            name="Fone Bluetooth",
            cost_price=Decimal("100.00"),
            sale_price=Decimal("250.00"),
            category=self.category,
            stock=5,
            description="Fone com cancelamento de ruído"
        )
        
        # 3. Criar Usuários e Clientes
        self.admin_user = User.objects.create_superuser(username="admin", password="admin123", email="admin@test.com")
        self.client_user = User.objects.create_user(username="joao", password="joao123", email="joao@test.com")
        
        self.client_profile = Client.objects.create(
            user=self.client_user,
            name="João da Silva",
            cpf_cnpj="123.456.789-00",
            birthday=date(1990, 5, 15),
            contact="(11) 98888-8888",
            address="Rua das Flores, 123 - São Paulo/SP"
        )
        
        self.http_client = HttpClient()

    def test_models_creation(self):
        """Verifica se os modelos básicos de categoria, produto e cliente foram criados com sucesso."""
        self.assertEqual(Category.objects.count(), 1)
        self.assertEqual(Product.objects.count(), 2)
        self.assertEqual(Client.objects.count(), 1)
        
        self.assertEqual(str(self.product1), "E001 - Smartphone X")
        self.assertEqual(self.client_profile.name, "João da Silva")
        self.assertEqual(self.client_profile.user.username, "joao")

    def test_catalog_view_and_filter(self):
        """Verifica a visualização pública do catálogo e filtros por categoria."""
        response = self.http_client.get('/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Smartphone X")
        self.assertContains(response, "Fone Bluetooth")
        
        # Inativar produto e checar se some do catálogo
        self.product2.is_active = False
        self.product2.save()
        
        response = self.http_client.get('/')
        self.assertContains(response, "Smartphone X")
        self.assertNotContains(response, "Fone Bluetooth")

    def test_cart_session_operations(self):
        """Verifica as operações básicas de adicionar e remover do carrinho usando a sessão do Django."""
        # Adicionar produto 1
        response = self.http_client.get(f'/carrinho/adicionar/{self.product1.id}/')
        self.assertEqual(response.status_code, 302) # Redirect to catalog
        
        # Verificar se está na sessão
        session = self.http_client.session
        self.assertIn('cart', session)
        self.assertEqual(session['cart'][str(self.product1.id)], 1)
        
        # Adicionar mais um do mesmo produto
        self.http_client.get(f'/carrinho/adicionar/{self.product1.id}/')
        session = self.http_client.session
        self.assertEqual(session['cart'][str(self.product1.id)], 2)
        
        # Remover do carrinho
        response = self.http_client.get(f'/carrinho/remover/{self.product1.id}/')
        self.assertEqual(response.status_code, 302) # Redirect to cart_view
        session = self.http_client.session
        self.assertNotIn(str(self.product1.id), session['cart'])

    def test_checkout_and_stock_deduction(self):
        """Verifica o fluxo completo de finalização do pedido, dedução de estoque e link de WhatsApp."""
        # Login do cliente
        self.http_client.login(username="joao", password="joao123")
        
        # Adicionar produtos ao carrinho
        self.http_client.get(f'/carrinho/adicionar/{self.product1.id}/') # Qty: 1
        self.http_client.get(f'/carrinho/adicionar/{self.product2.id}/') # Qty: 1
        
        # Enviar checkout via POST
        post_data = {
            'name': "João da Silva",
            'cpf_cnpj': "123.456.789-00",
            'birthday': "1990-05-15",
            'contact': "(11) 98888-8888",
            'address': "Rua das Flores, 123 - São Paulo/SP"
        }
        
        response = self.http_client.post('/finalizar/', post_data)
        self.assertEqual(response.status_code, 200) # Renderiza a página de sucesso
        
        # Verificar se a compra foi criada
        self.assertEqual(Purchase.objects.count(), 1)
        purchase = Purchase.objects.first()
        self.assertEqual(purchase.client, self.client_profile)
        self.assertEqual(purchase.total_value, Decimal("2750.00")) # 2500 + 250
        self.assertEqual(purchase.status, "Pendente")
        
        # Verificar se os itens foram criados
        self.assertEqual(purchase.items.count(), 2)
        
        # Verificar se o estoque foi abatido
        self.product1.refresh_from_db()
        self.product2.refresh_from_db()
        self.assertEqual(self.product1.stock, 9) # 10 - 1
        self.assertEqual(self.product2.stock, 4) # 5 - 1
        
        # Verificar se o carrinho foi esvaziado
        session = self.http_client.session
        self.assertEqual(session.get('cart', {}), {})

    def test_admin_dashboard_metrics(self):
        """Verifica as queries de KPIs financeiros no Dashboard do Administrador."""
        # Criar compras de teste
        # Compra 1: Finalizada (Entra nas métricas financeiras)
        p1 = Purchase.objects.create(client=self.client_profile, total_value=Decimal("5000.00"), status="Finalizada")
        PurchaseItem.objects.create(purchase=p1, product=self.product1, quantity=2, price=Decimal("2500.00"))
        
        # Compra 2: Pendente (Não entra no faturamento finalizado)
        p2 = Purchase.objects.create(client=self.client_profile, total_value=Decimal("250.00"), status="Pendente")
        PurchaseItem.objects.create(purchase=p2, product=self.product2, quantity=1, price=Decimal("250.00"))
        
        # Fazer login como admin
        self.http_client.login(username="admin", password="admin123")
        
        response = self.http_client.get('/dashboard/')
        self.assertEqual(response.status_code, 200)
        
        # Verificar se os dados no contexto do dashboard batem
        self.assertEqual(response.context['sales_today'], Decimal("5000.00"))
        self.assertEqual(response.context['sales_month'], Decimal("5000.00"))
        self.assertEqual(response.context['total_qty_sold'], 2)
        self.assertEqual(response.context['top_selling']['product__name'], "Smartphone X")
        self.assertEqual(response.context['top_client']['client__name'], "João da Silva")
        self.assertEqual(response.context['top_client']['total_spent'], Decimal("5000.00"))

    def test_permission_restrictions(self):
        """Valida que clientes comuns não conseguem entrar no Dashboard Administrativo."""
        # 1. Sem login (Anônimo) -> Deve redirecionar para a tela de login com prefixo next
        response = self.http_client.get('/dashboard/')
        self.assertRedirects(response, "/admin-django/login/?next=/dashboard/")
        
        # 2. Logado como cliente comum
        self.http_client.login(username="joao", password="joao123")
        response = self.http_client.get('/dashboard/')
        # O staff_member_required redireciona para a tela de login se não for staff
        self.assertRedirects(response, "/admin-django/login/?next=/dashboard/")
        
        # 3. Logado como staff adm
        self.http_client.login(username="admin", password="admin123")
        response = self.http_client.get('/dashboard/')
        self.assertEqual(response.status_code, 200)

    def test_new_features(self):
        """Testa as novas funcionalidades de bloqueio de status finalizado, novas categorias e carteira de clientes."""
        # Criar usuário staff simples (vendedor, não superuser)
        vendedor = User.objects.create_user(username="vendedor", password="vendedor123", email="vendedor@test.com")
        vendedor.is_staff = True
        vendedor.save()
        
        # Criar compra já finalizada
        purchase = Purchase.objects.create(client=self.client_profile, total_value=Decimal("100.00"), status="Finalizada")
        
        # 1. Testar bloqueio de status finalizado para vendedor (staff comum)
        self.http_client.login(username="vendedor", password="vendedor123")
        response = self.http_client.post(f'/dashboard/vendas/{purchase.id}/status/', {'status': 'Pendente'})
        self.assertRedirects(response, '/dashboard/')
        purchase.refresh_from_db()
        self.assertEqual(purchase.status, "Finalizada") # Não mudou!
        
        # 2. Testar liberação de status finalizado para superadministrador (superuser)
        self.http_client.login(username="admin", password="admin123")
        response = self.http_client.post(f'/dashboard/vendas/{purchase.id}/status/', {'status': 'Pendente'})
        self.assertRedirects(response, '/dashboard/')
        purchase.refresh_from_db()
        self.assertEqual(purchase.status, "Pendente") # Mudou!
        
        # 3. Testar criação de nova categoria pelo painel adm
        response = self.http_client.post('/dashboard/categorias/', {'name': 'Móveis'})
        self.assertEqual(response.status_code, 302) # Redirects back
        self.assertTrue(Category.objects.filter(slug='moveis').exists())
        
        # 4. Testar carteira de clientes dashboard
        response = self.http_client.get('/dashboard/carteira/')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "João da Silva")

