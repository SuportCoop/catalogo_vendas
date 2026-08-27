from django.urls import path
from . import views

urlpatterns = [
    # Cliente / Catálogo
    path('', views.catalog, name='catalog'),
    path('produto/<int:product_id>/', views.product_detail_json, name='product_detail_json'),
    path('carrinho/', views.cart_view, name='cart_view'),
    path('carrinho/adicionar/<int:product_id>/', views.cart_add, name='cart_add'),
    path('carrinho/remover/<int:product_id>/', views.cart_remove, name='cart_remove'),
    path('carrinho/atualizar/', views.cart_update, name='cart_update'),
    path('finalizar/', views.checkout, name='checkout'),
    path('historico/', views.purchase_history, name='purchase_history'),
    
    # Autenticação
    path('login/', views.client_login, name='login'),
    path('registro/', views.client_register, name='register'),
    path('logout/', views.client_logout, name='logout'),
    
    # Dashboard Admin & Financeiro
    path('dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('dashboard/vendas/nova/', views.admin_purchase_create, name='admin_purchase_create'),
    path('dashboard/vendas/', views.admin_purchases_list, name='admin_purchases_list'),
    path('dashboard/vendas/<int:purchase_id>/editar/', views.admin_purchase_edit, name='admin_purchase_edit'),
    path('dashboard/vendas/<int:purchase_id>/status/', views.update_purchase_status, name='update_purchase_status'),
    path('dashboard/produtos/', views.admin_products, name='admin_products'),
    path('dashboard/produtos/novo/', views.admin_product_create, name='admin_product_create'),
    path('dashboard/produtos/<int:product_id>/editar/', views.admin_product_edit, name='admin_product_edit'),
    path('dashboard/produtos/<int:product_id>/status/', views.toggle_product_status, name='toggle_product_status'),
    
    path('dashboard/clientes/', views.admin_clients, name='admin_clients'),
    path('dashboard/clientes/novo/', views.admin_client_create, name='admin_client_create'),
    path('dashboard/clientes/<int:client_id>/editar/', views.admin_client_edit, name='admin_client_edit'),
    path('dashboard/carteira/', views.admin_client_portfolio, name='admin_client_portfolio'),
    path('dashboard/categorias/', views.admin_categories, name='admin_categories'),
    
    path('dashboard/usuarios/', views.admin_users, name='admin_users'),
    path('dashboard/usuarios/novo/', views.admin_user_create, name='admin_user_create'),
    path('dashboard/usuarios/<int:user_id>/permissao/', views.admin_user_toggle_staff, name='admin_user_toggle_staff'),
]
