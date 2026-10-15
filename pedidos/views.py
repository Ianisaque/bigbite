from contas.decorators import tipo_required
from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from cardapio.models import Produto

from .carrinho import Carrinho
from .forms import CheckoutForm
from .models import ItemPedido, Pedido



@tipo_required('cliente')
def ver_carrinho(request):
    return render(request, 'pedidos/carrinho.html', Carrinho(request).resumo(request.user))

@tipo_required('cliente')
@require_POST
def adicionar(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id, disponivel=True)
    Carrinho(request).adicionar(produto.id)
    messages.success(request, f'{produto.nome} adicionado ao carrinho.')

    destino = request.POST.get('next', '')
    if not url_has_allowed_host_and_scheme(destino, allowed_hosts={request.get_host()}):
        destino = 'carrinho'
    return redirect(destino)


@tipo_required('cliente')
@require_POST
def atualizar(request, produto_id):
    try:
        quantidade = int(request.POST.get('quantidade', 1))
    except ValueError:
        quantidade = 1
    Carrinho(request).definir(produto_id, min(quantidade, 99))
    return redirect('carrinho')


@tipo_required('cliente')
@require_POST
def remover(request, produto_id):
    Carrinho(request).remover(produto_id)
    return redirect('carrinho')

@tipo_required('cliente')
def finalizar(request):
    carrinho = Carrinho(request)
    resumo = carrinho.resumo(request.user)

    if not resumo['itens']:
        messages.warning(request, 'Seu carrinho está vazio.')
        return redirect('cardapio')

    ultimo = request.user.pedidos.first()
    inicial = {'endereco_entrega': ultimo.endereco_entrega} if ultimo else {}
    form = CheckoutForm(request.POST or None, initial=inicial)

    if request.method == 'POST' and form.is_valid():
        with transaction.atomic():
            pedido = form.save(commit=False)
            pedido.cliente = request.user
            pedido.subtotal = resumo['subtotal']
            pedido.desconto = resumo['desconto']
            pedido.taxa_entrega = resumo['taxa_entrega']
            pedido.total = resumo['total']
            pedido.fidelidade_aplicada = resumo['fidelidade']
            pedido.save()

            ItemPedido.objects.bulk_create([
                ItemPedido(
                    pedido=pedido,
                    produto=item['produto'],
                    quantidade=item['quantidade'],
                    preco_unitario=item['produto'].preco,
                )
                for item in resumo['itens']
            ])

        carrinho.limpar()
        messages.success(request, f'Pedido #{pedido.pk} realizado com sucesso!')
        return redirect('pedido_detalhe', pk=pedido.pk)

    return render(request, 'pedidos/finalizar.html', {**resumo, 'form': form})


@tipo_required('cliente')
def historico(request):
    pedidos = request.user.pedidos.all()
    return render(request, 'pedidos/historico.html', {'pedidos': pedidos})


@tipo_required('cliente')
def pedido_detalhe(request, pk):
    pedido = get_object_or_404(
        Pedido.objects.prefetch_related('itens__produto'),
        pk=pk,
        cliente=request.user,
    )
    return render(request, 'pedidos/detalhe.html', {'pedido': pedido})