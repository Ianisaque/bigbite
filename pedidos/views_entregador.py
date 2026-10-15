from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from contas.decorators import tipo_required

from .models import Pedido


@tipo_required('entregador')
def entregas(request):
    base = (
        Pedido.objects.filter(entregador=request.user)
        .select_related('cliente')
        .prefetch_related('itens__produto')
    )
    return render(request, 'entregador/entregas.html', {
        'a_caminho': base.filter(status=Pedido.Status.SAIU).order_by('atualizado_em'),
        'no_destino': base.filter(status=Pedido.Status.CHEGOU).order_by('atualizado_em'),
        'entregues_hoje': base.filter(
            status__in=[Pedido.Status.ENTREGUE, Pedido.Status.FINALIZADO],
            atualizado_em__date=timezone.localdate(),
        ).order_by('-atualizado_em'),
    })


@tipo_required('entregador')
@require_POST
def avancar(request, pk):
    # só consegue mexer nos pedidos atribuídos a ele
    pedido = get_object_or_404(Pedido, pk=pk, entregador=request.user)
    acao = pedido.acao_entregador

    # evita clique duplo / tela desatualizada
    if not acao or request.POST.get('de') != pedido.status:
        messages.warning(request, f'O pedido #{pedido.pk} já foi atualizado.')
        return redirect('entregas')

    pedido.status = acao[0]
    pedido.save()
    messages.success(request, f'Pedido #{pedido.pk}: {pedido.get_status_display()}.')
    return redirect('entregas')