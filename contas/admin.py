from django.contrib import admin
from django.contrib.auth.admin import UserAdmin
from .models import Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    ordering = ('email',)
    list_display = ('email', 'nome', 'tipo', 'is_staff')
    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Dados', {'fields': ('nome', 'telefone', 'tipo')}),
        ('Permissões', {'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions')}),
    )
    add_fieldsets = (
        (None, {'classes': ('wide',), 'fields': ('email', 'nome', 'tipo', 'password1', 'password2')}),
    )
    search_fields = ('email', 'nome')