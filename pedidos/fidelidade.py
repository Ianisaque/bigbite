from decimal import ROUND_HALF_UP, Decimal

from .models import Pedido

CICLO = 5
PERCENTUAL_DESCONTO = Decimal('0.20')


def posicao_no_ciclo(cliente):
    """Posição do próximo pedido do cliente no ciclo: de 1 a 5."""
    anteriores = cliente.pedidos.exclude(status=Pedido.Status.CANCELADO).count()
    return anteriores % CICLO + 1


def tem_desconto(cliente):
    return posicao_no_ciclo(cliente) == CICLO


def calcular_desconto(subtotal):
    return (subtotal * PERCENTUAL_DESCONTO).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )