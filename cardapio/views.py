from django.db.models import Prefetch, Sum
from django.shortcuts import render

from pedidos.fidelidade import CICLO, posicao_no_ciclo
from pedidos.models import TAXA_ENTREGA, ItemPedido, Pedido

from .models import Categoria, Produto


def _categorias():
    disponiveis = Produto.objects.filter(disponivel=True)
    return Categoria.objects.prefetch_related(
        Prefetch('produtos', queryset=disponiveis)
    )


def _mais_pedidos(limite=3):
    """IDs dos produtos mais vendidos (ignora pedidos cancelados)."""
    ranking = (
        ItemPedido.objects.exclude(pedido__status=Pedido.Status.CANCELADO)
        .values('produto')
        .annotate(total=Sum('quantidade'))
        .order_by('-total')[:limite]
    )
    return [linha['produto'] for linha in ranking]


def home(request):
    mais_pedidos = _mais_pedidos()

    posicao = None
    if request.user.is_authenticated and request.user.tipo == 'cliente':
        posicao = posicao_no_ciclo(request.user)

    return render(request, 'cardapio/home.html', {
        'categorias': _categorias(),
        'mais_pedidos': mais_pedidos,
        'destaques': Produto.objects.filter(id__in=mais_pedidos, disponivel=True).select_related('categoria'),
        'taxa_entrega': TAXA_ENTREGA,
        'etapas': range(1, CICLO + 1),
        'posicao': posicao,
    })


def cardapio(request):
    return render(request, 'cardapio/cardapio.html', {
        'categorias': _categorias(),
        'mais_pedidos': _mais_pedidos(),
    })