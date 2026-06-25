from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone

class Category(models.Model):
    name = models.CharField(max_length=100, verbose_name="Nome")
    slug = models.SlugField(unique=True, verbose_name="Slug")

    class Meta:
        verbose_name = "Categoria"
        verbose_name_plural = "Categorias"

    def __str__(self):
        return self.name

class Product(models.Model):
    code = models.CharField(max_length=50, unique=True, verbose_name="Código do Produto")
    name = models.CharField(max_length=200, verbose_name="Nome")
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor de Custo")
    sale_price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Valor de Venda")
    category = models.ForeignKey(Category, on_delete=models.PROTECT, related_name="products", verbose_name="Categoria")
    stock = models.IntegerField(default=0, verbose_name="Quantidade em Estoque")
    description = models.TextField(verbose_name="Descrição do Produto")
    is_active = models.BooleanField(default=True, verbose_name="Ativo no Catálogo")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Produto"
        verbose_name_plural = "Produtos"

    def __str__(self):
        return f"{self.code} - {self.name}"

class ProductImage(models.Model):
    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="images")
    image = models.ImageField(upload_to="products/", verbose_name="Imagem")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Imagem do Produto"
        verbose_name_plural = "Imagens dos Produtos"

    def __str__(self):
        return f"Imagem de {self.product.name}"

class Client(models.Model):
    user = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="client_profile", verbose_name="Usuário Relacionado")
    name = models.CharField(max_length=200, verbose_name="Nome Completo")
    cpf_cnpj = models.CharField(max_length=20, verbose_name="CPF/CNPJ", blank=True, default="")
    birthday = models.DateField(verbose_name="Data de Aniversário", null=True, blank=True)
    contact = models.CharField(max_length=50, verbose_name="Contato/Telefone")
    address = models.TextField(verbose_name="Endereço Completo", blank=True, default="")

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"

    def __str__(self):
        return self.name

class Purchase(models.Model):
    STATUS_CHOICES = [
        ("Pendente", "Pendente"),
        ("Finalizada", "Finalizada"),
        ("Cancelada", "Cancelada"),
    ]
    client = models.ForeignKey(Client, on_delete=models.CASCADE, related_name="purchases", verbose_name="Cliente")
    date = models.DateTimeField(default=timezone.now, verbose_name="Data da Compra")
    total_value = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Valor Total")
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default="Pendente", verbose_name="Status")
    payment_method = models.CharField(max_length=50, default="PIX", verbose_name="Método de Pagamento")

    class Meta:
        verbose_name = "Compra"
        verbose_name_plural = "Compras"

    def __str__(self):
        return f"Compra #{self.id} - {self.client.name} ({self.status})"

class PurchaseItem(models.Model):
    purchase = models.ForeignKey(Purchase, on_delete=models.CASCADE, related_name="items", verbose_name="Compra")
    product = models.ForeignKey(Product, on_delete=models.PROTECT, related_name="purchase_items", verbose_name="Produto")
    quantity = models.IntegerField(default=1, verbose_name="Quantidade")
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name="Preço Unitário")

    class Meta:
        verbose_name = "Item de Compra"
        verbose_name_plural = "Itens de Compra"

    def __str__(self):
        return f"{self.quantity}x {self.product.name} na Compra #{self.purchase.id}"
