from django.urls import path

from . import views, views_entregador, views_loja

urlpatterns = [
    # Cliente
    path('carrinho/', views.ver_carrinho, name='carrinho'),
    path('carrinho/adicionar/<int:produto_id>/', views.adicionar, name='carrinho_adicionar'),
    path('carrinho/trio/<int:produto_id>/', views.alternar_trio, name='carrinho_trio'),
    path('carrinho/atualizar/<int:produto_id>/', views.atualizar, name='carrinho_atualizar'),
    path('carrinho/remover/<int:produto_id>/', views.remover, name='carrinho_remover'),
    path('carrinho/observacao/', views.salvar_observacao, name='carrinho_observacao'),
    path('pedido/finalizar/', views.finalizar, name='finalizar'),
    path('pedidos/', views.historico, name='historico'),
    path('pedidos/<int:pk>/', views.pedido_detalhe, name='pedido_detalhe'),

    # Loja
    path('loja/', views_loja.painel, name='painel'),
    path('loja/pedido/<int:pk>/avancar/', views_loja.avancar, name='painel_avancar'),
    path('loja/pedido/<int:pk>/entregador/', views_loja.atribuir, name='painel_entregador'),
    path('loja/pedido/<int:pk>/cancelar/', views_loja.cancelar, name='painel_cancelar'),

    # Entregador
    path('entregas/', views_entregador.entregas, name='entregas'),
    path('entregas/<int:pk>/avancar/', views_entregador.avancar, name='entrega_avancar'),
]