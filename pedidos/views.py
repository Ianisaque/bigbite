from django.contrib import messages
from django.db import transaction
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from cardapio.models import Produto
from contas.decorators import tipo_required

from .carrinho import Carrinho
from .forms import CheckoutForm
from .models import ItemPedido, Pedido


@tipo_required('cliente')
def ver_carrinho(request):
    carrinho = Carrinho(request)
    contexto = {**carrinho.resumo(request.user), 'observacao': carrinho.observacao}
    return render(request, 'pedidos/carrinho.html', contexto)


@tipo_required('cliente')
@require_POST
def salvar_observacao(request):
    Carrinho(request).definir_observacao(request.POST.get('observacao', ''))
    if request.POST.get('destino') == 'cardapio':
        return redirect('cardapio')
    return redirect('finalizar')

@tipo_required('cliente')
@require_POST
def adicionar(request, produto_id):
    produto = get_object_or_404(Produto, id=produto_id, disponivel=True)
    trio = request.POST.get('trio') == 'on' and produto.permite_trio
    Carrinho(request).adicionar(produto.id, trio=trio)

    nome = f'{produto.nome} (trio)' if trio else produto.nome
    messages.success(request, f'{nome} adicionado ao carrinho.')

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
    trio = request.POST.get('trio') == '1'
    Carrinho(request).definir(produto_id, min(quantidade, 99), trio=trio)
    return redirect('carrinho')


@tipo_required('cliente')
@require_POST
def remover(request, produto_id):
    trio = request.POST.get('trio') == '1'
    Carrinho(request).remover(produto_id, trio=trio)
    return redirect('carrinho')


@tipo_required('cliente')
@require_POST
def alternar_trio(request, produto_id):
    """Transforma uma unidade do lanche em trio (ou volta para só o lanche)."""
    produto = get_object_or_404(Produto, id=produto_id, disponivel=True)
    if produto.permite_trio:
        Carrinho(request).converter(produto.id, para_trio=request.POST.get('para') == 'trio')
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
            pedido.observacao = carrinho.observacao
            pedido.save()

            ItemPedido.objects.bulk_create([
                ItemPedido(
                    pedido=pedido,
                    produto=item['produto'],
                    quantidade=item['quantidade'],
                    trio=item['trio'],
                    preco_unitario=item['preco_unitario'],
                )
                for item in resumo['itens']
            ])

        carrinho.limpar()
        messages.success(request, f'Pedido #{pedido.pk} realizado com sucesso!')
        return redirect('pedido_detalhe', pk=pedido.pk)

    return render(request, 'pedidos/finalizar.html', {**resumo, 'form': form, 'observacao': carrinho.observacao})


@tipo_required('cliente')
def historico(request):
    pedidos = request.user.pedidos.prefetch_related('itens__produto')
    return render(request, 'pedidos/historico.html', {'pedidos': pedidos})


@tipo_required('cliente')
def pedido_detalhe(request, pk):
    pedido = get_object_or_404(
        Pedido.objects.prefetch_related('itens__produto'),
        pk=pk,
        cliente=request.user,
    )
    return render(request, 'pedidos/detalhe.html', {'pedido': pedido})
