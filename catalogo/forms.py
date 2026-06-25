from django import forms
from django.contrib.auth.models import User
from .models import Product, Client, Category

class ProductForm(forms.ModelForm):
    class Meta:
        model = Product
        fields = ["code", "name", "cost_price", "sale_price", "category", "stock", "description", "is_active"]
        widgets = {
            "code": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: PROD001"}),
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nome do produto"}),
            "cost_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "placeholder": "0.00"}),
            "sale_price": forms.NumberInput(attrs={"class": "form-control", "step": "0.01", "placeholder": "0.00"}),
            "category": forms.Select(attrs={"class": "form-select"}),
            "stock": forms.NumberInput(attrs={"class": "form-control", "placeholder": "0"}),
            "description": forms.Textarea(attrs={"class": "form-control", "rows": "4", "placeholder": "Descreva o produto..."}),
            "is_active": forms.CheckboxInput(attrs={"class": "form-check-input"}),
        }

class ClientForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ["name", "cpf_cnpj", "birthday", "contact", "address"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nome completo"}),
            "cpf_cnpj": forms.TextInput(attrs={"class": "form-control", "placeholder": "CPF ou CNPJ"}),
            "birthday": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "contact": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: (11) 99999-9999"}),
            "address": forms.Textarea(attrs={"class": "form-control", "rows": "3", "placeholder": "Endereço de entrega"}),
        }

class UserCreateForm(forms.ModelForm):
    password = forms.CharField(label="Senha", widget=forms.PasswordInput(attrs={"class": "form-control", "placeholder": "Senha"}))
    is_staff = forms.BooleanField(label="Acesso Administrativo (Staff)", required=False, widget=forms.CheckboxInput(attrs={"class": "form-check-input"}))

    class Meta:
        model = User
        fields = ["username", "email", "password", "is_staff"]
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nome de usuário"}),
            "email": forms.EmailInput(attrs={"class": "form-control", "placeholder": "E-mail"}),
        }

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user

class CategoryForm(forms.ModelForm):
    class Meta:
        model = Category
        fields = ["name"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nome da nova categoria"}),
        }

class CheckoutForm(forms.ModelForm):
    class Meta:
        model = Client
        fields = ["name", "birthday", "contact"]
        widgets = {
            "name": forms.TextInput(attrs={"class": "form-control", "placeholder": "Nome completo"}),
            "birthday": forms.DateInput(attrs={"class": "form-control", "type": "date"}),
            "contact": forms.TextInput(attrs={"class": "form-control", "placeholder": "Ex: (11) 99999-9999"}),
        }

