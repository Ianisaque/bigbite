from django.contrib import messages
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from contas.decorators import tipo_required

from .models import Pedido

Usuario = get_user_model()

ABAS = [
    ('ativos', 'Em andamento'),
    ('finalizado', 'Finalizados'),
    ('cancelado', 'Cancelados'),
    ('todos', 'Todos'),
]


def _entregadores():
    return Usuario.objects.filter(tipo='entregador', is_active=True).order_by('nome')


@tipo_required('loja')
def painel(request):
    filtro = request.GET.get('status', 'ativos')
    pedidos = Pedido.objects.select_related('cliente', 'entregador').prefetch_related('itens__produto')

    if filtro == 'ativos':
        pedidos = pedidos.exclude(
            status__in=[Pedido.Status.FINALIZADO, Pedido.Status.CANCELADO]
        ).order_by('criado_em')  # o mais antigo primeiro (fila)
    elif filtro in ('finalizado', 'cancelado'):
        pedidos = pedidos.filter(status=filtro)
    else:
        filtro = 'todos'

    return render(request, 'loja/painel.html', {
        'pedidos': pedidos,
        'filtro': filtro,
        'abas': ABAS,
        'entregadores': _entregadores(),
    })


@tipo_required('loja')
@require_POST
def avancar(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)

    # evita clique duplo / duas abas abertas com tela desatualizada
    if request.POST.get('de') != pedido.status or not pedido.acao_loja:
        messages.warning(request, f'O pedido #{pedido.pk} já foi atualizado. Veja o status atual.')
        return redirect('painel')

    novo_status = pedido.proximo_status

    if novo_status == Pedido.Status.SAIU:
        entregador = _entregadores().filter(pk=request.POST.get('entregador') or 0).first()
        if entregador:
            pedido.entregador = entregador
        if not pedido.entregador:
            messages.error(request, 'Escolha um entregador antes de enviar o pedido.')
            return redirect('painel')

    pedido.status = novo_status
    pedido.save()
    messages.success(request, f'Pedido #{pedido.pk}: {pedido.get_status_display()}.')
    return redirect('painel')


@tipo_required('loja')
@require_POST
def atribuir(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    entregador = _entregadores().filter(pk=request.POST.get('entregador') or 0).first()

    if entregador and pedido.status in (Pedido.Status.PREPARO, Pedido.Status.SAIU):
        pedido.entregador = entregador
        pedido.save()
        messages.success(request, f'Pedido #{pedido.pk}: entregador {entregador.nome}.')
    else:
        messages.error(request, 'Não foi possível definir o entregador.')
    return redirect('painel')


@tipo_required('loja')
@require_POST
def cancelar(request, pk):
    pedido = get_object_or_404(Pedido, pk=pk)
    if pedido.pode_cancelar:
        pedido.status = Pedido.Status.CANCELADO
        pedido.save()
        messages.success(request, f'Pedido #{pedido.pk} cancelado.')
    else:
        messages.error(request, 'Esse pedido não pode mais ser cancelado.')
    return redirect('painel')