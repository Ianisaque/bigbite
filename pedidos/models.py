from decimal import Decimal

from django.conf import settings
from django.db import models

from cardapio.models import Produto

TAXA_ENTREGA = Decimal('7.00')

ADICIONAL_TRIO = Decimal('15.00')

class Pedido(models.Model):
    class Status(models.TextChoices):
        FEITO = 'feito', 'Pedido feito'
        RECEBIDO = 'recebido', 'Recebido'
        PREPARO = 'preparo', 'Em preparo'
        SAIU = 'saiu', 'Saiu para entrega'
        CHEGOU = 'chegou', 'Chegou'
        ENTREGUE = 'entregue', 'Entregue'
        FINALIZADO = 'finalizado', 'Finalizado'
        CANCELADO = 'cancelado', 'Cancelado'

    class Pagamento(models.TextChoices):
        DINHEIRO = 'dinheiro', 'Dinheiro'
        CARTAO = 'cartao', 'Cartão na entrega'
        PIX = 'pix', 'Pix'

    cliente = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name='pedidos'
    )
    entregador = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.SET_NULL,
        null=True, blank=True, related_name='entregas',
        limit_choices_to={'tipo': 'entregador'},
    )
    status = models.CharField(
        max_length=12, choices=Status.choices, default=Status.FEITO
    )
    forma_pagamento = models.CharField(max_length=10, choices=Pagamento.choices)
    endereco_entrega = models.TextField()
    observacao = models.TextField('Observações', blank=True, default='')

    subtotal = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    desconto = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    taxa_entrega = models.DecimalField(
        max_digits=6, decimal_places=2, default=TAXA_ENTREGA
    )
    total = models.DecimalField(max_digits=8, decimal_places=2, default=0)
    fidelidade_aplicada = models.BooleanField(default=False)

    criado_em = models.DateTimeField(auto_now_add=True)
    atualizado_em = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ['-criado_em']

    # status atual -> (próximo status, texto do botão)
    FLUXO_LOJA = {
        Status.FEITO.value: (Status.RECEBIDO.value, 'Confirmar recebimento'),
        Status.RECEBIDO.value: (Status.PREPARO.value, 'Iniciar preparo'),
        Status.PREPARO.value: (Status.SAIU.value, 'Saiu para entrega'),
        Status.ENTREGUE.value: (Status.FINALIZADO.value, 'Pagamento recebido: finalizar'),
    }
    FLUXO_ENTREGADOR = {
        Status.SAIU.value: (Status.CHEGOU.value, 'Cheguei ao destino'),
        Status.CHEGOU.value: (Status.ENTREGUE.value, 'Entregue'),
    }
    STATUS_CANCELAVEIS = (
        Status.FEITO.value, Status.RECEBIDO.value, Status.PREPARO.value,
    )

    @property
    def acao_loja(self):
        return self.FLUXO_LOJA.get(self.status)

    @property
    def proximo_status(self):
        acao = self.acao_loja
        return acao[0] if acao else None

    @property
    def rotulo_acao(self):
        acao = self.acao_loja
        return acao[1] if acao else ''

    @property
    def acao_entregador(self):
        return self.FLUXO_ENTREGADOR.get(self.status)

    @property
    def rotulo_acao_entregador(self):
        acao = self.acao_entregador
        return acao[1] if acao else ''

    @property
    def pode_cancelar(self):
        return self.status in self.STATUS_CANCELAVEIS

    ETAPAS = [
    (Status.FEITO.value, 'Pedido feito', 'ph-check'),
    (Status.RECEBIDO.value, 'Recebido', 'ph-check'),
    (Status.PREPARO.value, 'Em preparo', 'ph-check'),
    (Status.SAIU.value, 'A caminho', 'ph-check'),
    (Status.CHEGOU.value, 'Chegou', 'ph-check'),
    (Status.ENTREGUE.value, 'Entregue', 'ph-check'),
    (Status.FINALIZADO.value, 'Finalizado', 'ph-check'),
    ]

    @property
    def linha_do_tempo(self):
        valores = [valor for valor, _, _ in self.ETAPAS]
        if self.status not in valores:  # pedido cancelado
            return []

        atual = valores.index(self.status)
        finalizado = self.status == self.Status.FINALIZADO

        etapas = []
        for i, (_, rotulo, icone) in enumerate(self.ETAPAS):
            if i < atual or finalizado:
                estado = 'feito'
            elif i == atual:
                estado = 'atual'
            else:
                estado = 'pendente'
            etapas.append({'rotulo': rotulo, 'icone': icone, 'estado': estado})
        return etapas

    def __str__(self):
        return f'Pedido #{self.pk} - {self.cliente}'


class ItemPedido(models.Model):
    pedido = models.ForeignKey(
        Pedido, on_delete=models.CASCADE, related_name='itens'
    )
    trio = models.BooleanField(default=False)

    @property
    def descricao(self):
        if self.trio:
            return f'{self.produto.nome} em trio (+ batata e refri lata)'
        return self.produto.nome
    
    produto = models.ForeignKey(Produto, on_delete=models.PROTECT)
    quantidade = models.PositiveIntegerField(default=1)
    preco_unitario = models.DecimalField(max_digits=8, decimal_places=2)

    @property
    def subtotal(self):
        return self.quantidade * self.preco_unitario

    def __str__(self):
        return f'{self.quantidade}x {self.produto}'