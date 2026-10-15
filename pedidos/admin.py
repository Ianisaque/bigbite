from django.contrib import admin
from .models import Pedido, ItemPedido


class ItemInline(admin.TabularInline):
    model = ItemPedido
    extra = 0


@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    list_display = ('id', 'cliente', 'status', 'forma_pagamento', 'total', 'criado_em')
    list_filter = ('status',)
    inlines = [ItemInline]