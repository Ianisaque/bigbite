from django.urls import reverse

from .models import Pedido
from .tests import SENHA, BaseTestCase, criar_pedido


class ObservacaoTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.login(email='cliente@teste.com', password=SENHA)
        self.client.post(reverse('carrinho_adicionar', args=[self.burguer.id]))

    def test_observacao_vai_para_o_pedido(self):
        resp = self.client.post(
            reverse('carrinho_observacao'),
            {'observacao': 'Sem cebola, por favor', 'destino': 'finalizar'},
        )
        self.assertRedirects(resp, reverse('finalizar'))
        self.client.post(reverse('finalizar'), {
            'endereco_entrega': 'Rua A, 1', 'forma_pagamento': 'pix',
        })
        self.assertEqual(Pedido.objects.get().observacao, 'Sem cebola, por favor')

    def test_observacao_e_cortada_em_300_caracteres(self):
        self.client.post(reverse('carrinho_observacao'), {'observacao': 'a' * 500})
        self.client.post(reverse('finalizar'), {
            'endereco_entrega': 'Rua A, 1', 'forma_pagamento': 'pix',
        })
        self.assertEqual(len(Pedido.objects.get().observacao), 300)

    def test_continuar_pedindo_volta_ao_cardapio(self):
        resp = self.client.post(
            reverse('carrinho_observacao'),
            {'observacao': 'x', 'destino': 'cardapio'},
        )
        self.assertRedirects(resp, reverse('cardapio'))

    def test_observacao_e_limpa_depois_do_pedido(self):
        self.client.post(reverse('carrinho_observacao'), {'observacao': 'Sem cebola'})
        self.client.post(reverse('finalizar'), {
            'endereco_entrega': 'Rua A, 1', 'forma_pagamento': 'pix',
        })
        self.client.post(reverse('carrinho_adicionar', args=[self.burguer.id]))
        resp = self.client.get(reverse('carrinho'))
        self.assertEqual(resp.context['observacao'], '')

    def test_loja_ve_a_observacao(self):
        pedido = criar_pedido(self.cliente, observacao='Sem cebola')
        self.client.logout()
        self.client.login(email='loja@teste.com', password=SENHA)
        self.assertContains(self.client.get(reverse('painel')), 'Sem cebola')
