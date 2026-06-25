from django.contrib import admin
from .models import Category, Product, ProductImage, Client, Purchase, PurchaseItem

@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ("name", "slug")
    prepopulated_fields = {"slug": ("name",)}
    search_fields = ("name",)

class ProductImageInline(admin.TabularInline):
    model = ProductImage
    extra = 1
    max_num = 6

@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    list_display = ("code", "name", "cost_price", "sale_price", "stock", "is_active")
    list_filter = ("is_active", "category")
    search_fields = ("code", "name", "description")
    inlines = [ProductImageInline]

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ("name", "cpf_cnpj", "contact", "user")
    search_fields = ("name", "cpf_cnpj", "contact")

class PurchaseItemInline(admin.TabularInline):
    model = PurchaseItem
    extra = 0

@admin.register(Purchase)
class PurchaseAdmin(admin.ModelAdmin):
    list_display = ("id", "client", "date", "total_value", "status")
    list_filter = ("status", "date")
    search_fields = ("client__name", "id")
    inlines = [PurchaseItemInline]

@admin.register(PurchaseItem)
class PurchaseItemAdmin(admin.ModelAdmin):
    list_display = ("purchase", "product", "quantity", "price")
