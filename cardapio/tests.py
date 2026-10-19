from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from pedidos.models import ItemPedido, Pedido

from .models import Categoria, Produto
from .views import _mais_pedidos

Usuario = get_user_model()


class CardapioTests(TestCase):
    def setUp(self):
        categoria = Categoria.objects.create(nome='Lanches')
        self.visivel = Produto.objects.create(
            categoria=categoria, nome='X-Bacon', preco=Decimal('20.00')
        )
        self.oculto = Produto.objects.create(
            categoria=categoria, nome='Lanche Escondido', preco=Decimal('10.00'), disponivel=False
        )

    def test_home_abre_para_visitante(self):
        self.assertEqual(self.client.get(reverse('home')).status_code, 200)

    def test_cardapio_mostra_so_produtos_disponiveis(self):
        resposta = self.client.get(reverse('cardapio'))
        self.assertContains(resposta, 'X-Bacon')
        self.assertNotContains(resposta, 'Lanche Escondido')

    def test_visitante_ve_botao_para_entrar_e_nao_para_adicionar(self):
        resposta = self.client.get(reverse('cardapio'))
        self.assertContains(resposta, 'Entre para pedir')
        self.assertNotContains(resposta, 'Adicionar')

    def test_mais_pedidos_ignora_cancelados(self):
        cliente = Usuario.objects.create_user(email='c@teste.com', password='x-Senha-1234', nome='C')
        cancelado = Pedido.objects.create(
            cliente=cliente, status=Pedido.Status.CANCELADO,
            forma_pagamento='pix', endereco_entrega='Rua A',
        )
        ItemPedido.objects.create(
            pedido=cancelado, produto=self.visivel, quantidade=10, preco_unitario=Decimal('20.00')
        )
        self.assertEqual(_mais_pedidos(), [])

    def test_pagina_inexistente_mostra_404_personalizado(self):
        resposta = self.client.get('/essa-pagina-nao-existe/')
        self.assertEqual(resposta.status_code, 404)
        self.assertContains(resposta, 'não está no cardápio', status_code=404)
