from decimal import Decimal

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from cardapio.models import Categoria, Produto

from .fidelidade import calcular_desconto, posicao_no_ciclo, tem_desconto
from .models import ItemPedido, Pedido, TAXA_ENTREGA

Usuario = get_user_model()
SENHA = 'Senha-Forte-9137'


def criar_usuario(email, tipo='cliente', nome='Fulano'):
    return Usuario.objects.create_user(email=email, password=SENHA, nome=nome, tipo=tipo)


def criar_pedido(cliente, status=Pedido.Status.FEITO, **extra):
    return Pedido.objects.create(
        cliente=cliente,
        status=status,
        forma_pagamento='pix',
        endereco_entrega='Rua A, 1',
        **extra,
    )


class BaseTestCase(TestCase):
    """Cria categoria, produtos e usuários usados na maioria dos testes."""

    def setUp(self):
        categoria = Categoria.objects.create(nome='Lanches')
        self.burguer = Produto.objects.create(
            categoria=categoria, nome='X-Burguer', preco=Decimal('15.00')
        )
        self.refri = Produto.objects.create(
            categoria=categoria, nome='Refrigerante Lata', preco=Decimal('6.00')
        )
        self.cliente = criar_usuario('cliente@teste.com')
        self.loja = criar_usuario('loja@teste.com', tipo='loja', nome='Loja')
        self.entregador = criar_usuario('entregador@teste.com', tipo='entregador', nome='Moto')


# ---------------------------------------------------------------- fidelidade
class FidelidadeTests(BaseTestCase):
    def test_cliente_novo_comeca_na_posicao_1(self):
        self.assertEqual(posicao_no_ciclo(self.cliente), 1)
        self.assertFalse(tem_desconto(self.cliente))

    def test_quinto_pedido_tem_desconto(self):
        for _ in range(4):
            criar_pedido(self.cliente)
        self.assertEqual(posicao_no_ciclo(self.cliente), 5)
        self.assertTrue(tem_desconto(self.cliente))

    def test_pedido_cancelado_nao_conta(self):
        for _ in range(3):
            criar_pedido(self.cliente)
        criar_pedido(self.cliente, status=Pedido.Status.CANCELADO)
        self.assertEqual(posicao_no_ciclo(self.cliente), 4)
        self.assertFalse(tem_desconto(self.cliente))

    def test_ciclo_reinicia_depois_do_quinto(self):
        for _ in range(5):
            criar_pedido(self.cliente)
        self.assertEqual(posicao_no_ciclo(self.cliente), 1)

    def test_desconto_e_20_por_cento(self):
        self.assertEqual(calcular_desconto(Decimal('50.00')), Decimal('10.00'))

    def test_desconto_arredonda_para_centavos(self):
        # 12,34 * 20% = 2,468 -> 2,47
        self.assertEqual(calcular_desconto(Decimal('12.34')), Decimal('2.47'))


# ------------------------------------------------------------------ carrinho
class CarrinhoTests(BaseTestCase):
    def test_visitante_e_enviado_para_o_login(self):
        resposta = self.client.get(reverse('carrinho'))
        self.assertEqual(resposta.status_code, 302)
        self.assertIn(reverse('login'), resposta.url)

    def test_loja_nao_acessa_carrinho(self):
        self.client.force_login(self.loja)
        self.assertEqual(self.client.get(reverse('carrinho')).status_code, 403)

    def test_adicionar_soma_quantidade(self):
        self.client.force_login(self.cliente)
        url = reverse('carrinho_adicionar', args=[self.burguer.id])
        self.client.post(url)
        self.client.post(url)
        self.assertEqual(self.client.session['carrinho'], {str(self.burguer.id): 2})

    def test_produto_indisponivel_nao_entra_no_carrinho(self):
        self.refri.disponivel = False
        self.refri.save()
        self.client.force_login(self.cliente)
        resposta = self.client.post(reverse('carrinho_adicionar', args=[self.refri.id]))
        self.assertEqual(resposta.status_code, 404)

    def test_next_externo_e_ignorado(self):
        self.client.force_login(self.cliente)
        resposta = self.client.post(
            reverse('carrinho_adicionar', args=[self.burguer.id]),
            {'next': 'https://site-malicioso.com/'},
        )
        self.assertRedirects(resposta, reverse('carrinho'), fetch_redirect_response=False)

    def test_atualizar_para_zero_remove_o_item(self):
        self.client.force_login(self.cliente)
        self.client.post(reverse('carrinho_adicionar', args=[self.burguer.id]))
        self.client.post(reverse('carrinho_atualizar', args=[self.burguer.id]), {'quantidade': 0})
        self.assertEqual(self.client.session['carrinho'], {})

    def test_quantidade_maxima_e_99(self):
        self.client.force_login(self.cliente)
        self.client.post(reverse('carrinho_atualizar', args=[self.burguer.id]), {'quantidade': 500})
        self.assertEqual(self.client.session['carrinho'][str(self.burguer.id)], 99)

    def test_quantidade_invalida_vira_1(self):
        self.client.force_login(self.cliente)
        self.client.post(reverse('carrinho_atualizar', args=[self.burguer.id]), {'quantidade': 'abc'})
        self.assertEqual(self.client.session['carrinho'][str(self.burguer.id)], 1)

    def test_remover_item(self):
        self.client.force_login(self.cliente)
        self.client.post(reverse('carrinho_adicionar', args=[self.burguer.id]))
        self.client.post(reverse('carrinho_remover', args=[self.burguer.id]))
        self.assertEqual(self.client.session['carrinho'], {})

    def test_total_inclui_taxa_de_entrega(self):
        self.client.force_login(self.cliente)
        url = reverse('carrinho_adicionar', args=[self.burguer.id])
        self.client.post(url)
        self.client.post(url)
        resposta = self.client.get(reverse('carrinho'))
        self.assertEqual(resposta.context['subtotal'], Decimal('30.00'))
        self.assertEqual(TAXA_ENTREGA, Decimal('7.00'))
        self.assertEqual(resposta.context['total'], Decimal('37.00'))


# ------------------------------------------------------------------ checkout
class CheckoutTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.client.force_login(self.cliente)

    def _adicionar(self, produto, vezes=1):
        for _ in range(vezes):
            self.client.post(reverse('carrinho_adicionar', args=[produto.id]))

    def test_carrinho_vazio_volta_para_o_cardapio(self):
        resposta = self.client.get(reverse('finalizar'))
        self.assertRedirects(resposta, reverse('cardapio'), fetch_redirect_response=False)

    def test_finalizar_cria_pedido_e_itens(self):
        self._adicionar(self.burguer, 2)
        self._adicionar(self.refri)
        resposta = self.client.post(reverse('finalizar'), {
            'endereco_entrega': 'Rua A, 10',
            'forma_pagamento': 'pix',
        })

        pedido = Pedido.objects.get()
        self.assertRedirects(resposta, reverse('pedido_detalhe', args=[pedido.pk]),
                             fetch_redirect_response=False)
        self.assertEqual(pedido.cliente, self.cliente)
        self.assertEqual(pedido.status, Pedido.Status.FEITO)
        self.assertEqual(pedido.subtotal, Decimal('36.00'))
        self.assertEqual(pedido.desconto, Decimal('0'))
        self.assertEqual(pedido.total, Decimal('43.00'))
        self.assertFalse(pedido.fidelidade_aplicada)
        self.assertEqual(ItemPedido.objects.filter(pedido=pedido).count(), 2)

    def test_finalizar_limpa_o_carrinho(self):
        self._adicionar(self.burguer)
        self.client.post(reverse('finalizar'), {
            'endereco_entrega': 'Rua A, 10',
            'forma_pagamento': 'dinheiro',
        })
        self.assertEqual(self.client.session['carrinho'], {})

    def test_quinto_pedido_ganha_20_por_cento_nos_itens(self):
        for _ in range(4):
            criar_pedido(self.cliente, status=Pedido.Status.FINALIZADO)
        caro = Produto.objects.create(
            categoria=self.burguer.categoria, nome='Combo', preco=Decimal('50.00')
        )
        self._adicionar(caro)
        self.client.post(reverse('finalizar'), {
            'endereco_entrega': 'Rua A, 10',
            'forma_pagamento': 'cartao',
        })

        pedido = Pedido.objects.order_by('-criado_em', '-pk').first()
        self.assertTrue(pedido.fidelidade_aplicada)
        self.assertEqual(pedido.desconto, Decimal('10.00'))   # 20% só nos itens
        self.assertEqual(pedido.total, Decimal('47.00'))      # 50 - 10 + 7 de taxa

    def test_sem_endereco_nao_cria_pedido(self):
        self._adicionar(self.burguer)
        resposta = self.client.post(reverse('finalizar'), {
            'endereco_entrega': '',
            'forma_pagamento': 'pix',
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(Pedido.objects.count(), 0)

    def test_forma_de_pagamento_invalida_nao_cria_pedido(self):
        self._adicionar(self.burguer)
        resposta = self.client.post(reverse('finalizar'), {
            'endereco_entrega': 'Rua A, 10',
            'forma_pagamento': 'fiado',
        })
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(Pedido.objects.count(), 0)

    def test_preco_do_item_fica_congelado_no_pedido(self):
        self._adicionar(self.burguer)
        self.client.post(reverse('finalizar'), {
            'endereco_entrega': 'Rua A, 10',
            'forma_pagamento': 'pix',
        })
        self.burguer.preco = Decimal('99.00')
        self.burguer.save()
        self.assertEqual(ItemPedido.objects.get().preco_unitario, Decimal('15.00'))


# --------------------------------------------------------------- permissões
class PermissoesTests(BaseTestCase):
    def test_cliente_nao_acessa_painel_da_loja(self):
        self.client.force_login(self.cliente)
        self.assertEqual(self.client.get(reverse('painel')).status_code, 403)

    def test_cliente_nao_acessa_entregas(self):
        self.client.force_login(self.cliente)
        self.assertEqual(self.client.get(reverse('entregas')).status_code, 403)

    def test_entregador_nao_acessa_painel_da_loja(self):
        self.client.force_login(self.entregador)
        self.assertEqual(self.client.get(reverse('painel')).status_code, 403)

    def test_loja_nao_acessa_historico(self):
        self.client.force_login(self.loja)
        self.assertEqual(self.client.get(reverse('historico')).status_code, 403)

    def test_cliente_nao_ve_pedido_de_outro_cliente(self):
        outro = criar_usuario('outro@teste.com')
        pedido = criar_pedido(outro)
        self.client.force_login(self.cliente)
        resposta = self.client.get(reverse('pedido_detalhe', args=[pedido.pk]))
        self.assertEqual(resposta.status_code, 404)

    def test_cliente_nao_age_no_painel(self):
        pedido = criar_pedido(self.cliente)
        self.client.force_login(self.cliente)
        resposta = self.client.post(reverse('painel_avancar', args=[pedido.pk]), {'de': 'feito'})
        self.assertEqual(resposta.status_code, 403)
        pedido.refresh_from_db()
        self.assertEqual(pedido.status, Pedido.Status.FEITO)

    def test_visitante_nao_acessa_historico(self):
        resposta = self.client.get(reverse('historico'))
        self.assertEqual(resposta.status_code, 302)


# ------------------------------------------------------- fluxo de status
class FluxoStatusTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        self.pedido = criar_pedido(self.cliente)

    def _loja_avanca(self, **dados):
        self.client.force_login(self.loja)
        dados.setdefault('de', self.pedido.status)
        resposta = self.client.post(reverse('painel_avancar', args=[self.pedido.pk]), dados)
        self.pedido.refresh_from_db()
        return resposta

    def _entregador_avanca(self, usuario=None):
        self.client.force_login(usuario or self.entregador)
        resposta = self.client.post(
            reverse('entrega_avancar', args=[self.pedido.pk]), {'de': self.pedido.status}
        )
        self.pedido.refresh_from_db()
        return resposta

    def test_loja_confirma_e_inicia_preparo(self):
        self._loja_avanca()
        self.assertEqual(self.pedido.status, Pedido.Status.RECEBIDO)
        self._loja_avanca()
        self.assertEqual(self.pedido.status, Pedido.Status.PREPARO)

    def test_sair_para_entrega_exige_entregador(self):
        self.pedido.status = Pedido.Status.PREPARO
        self.pedido.save()
        self._loja_avanca()
        self.assertEqual(self.pedido.status, Pedido.Status.PREPARO)

    def test_sair_para_entrega_com_entregador(self):
        self.pedido.status = Pedido.Status.PREPARO
        self.pedido.save()
        self._loja_avanca(entregador=self.entregador.pk)
        self.assertEqual(self.pedido.status, Pedido.Status.SAIU)
        self.assertEqual(self.pedido.entregador, self.entregador)

    def test_nao_aceita_entregador_que_nao_e_entregador(self):
        self.pedido.status = Pedido.Status.PREPARO
        self.pedido.save()
        self._loja_avanca(entregador=self.cliente.pk)
        self.assertEqual(self.pedido.status, Pedido.Status.PREPARO)
        self.assertIsNone(self.pedido.entregador)

    def test_tela_desatualizada_nao_avanca(self):
        self._loja_avanca(de='preparo')  # o pedido ainda está em "feito"
        self.assertEqual(self.pedido.status, Pedido.Status.FEITO)

    def test_entregador_marca_chegou_e_entregue(self):
        self.pedido.status = Pedido.Status.SAIU
        self.pedido.entregador = self.entregador
        self.pedido.save()
        self._entregador_avanca()
        self.assertEqual(self.pedido.status, Pedido.Status.CHEGOU)
        self._entregador_avanca()
        self.assertEqual(self.pedido.status, Pedido.Status.ENTREGUE)

    def test_entregador_nao_mexe_em_pedido_de_outro(self):
        outro = criar_usuario('outro-moto@teste.com', tipo='entregador')
        self.pedido.status = Pedido.Status.SAIU
        self.pedido.entregador = self.entregador
        self.pedido.save()
        resposta = self._entregador_avanca(usuario=outro)
        self.assertEqual(resposta.status_code, 404)
        self.assertEqual(self.pedido.status, Pedido.Status.SAIU)

    def test_loja_finaliza_depois_da_entrega(self):
        self.pedido.status = Pedido.Status.ENTREGUE
        self.pedido.save()
        self._loja_avanca()
        self.assertEqual(self.pedido.status, Pedido.Status.FINALIZADO)

    def test_loja_nao_marca_chegou_nem_entregue(self):
        # essas etapas são do entregador
        self.pedido.status = Pedido.Status.SAIU
        self.pedido.entregador = self.entregador
        self.pedido.save()
        self._loja_avanca()
        self.assertEqual(self.pedido.status, Pedido.Status.SAIU)

    def test_cancelar_pedido_em_aberto(self):
        self.client.force_login(self.loja)
        self.client.post(reverse('painel_cancelar', args=[self.pedido.pk]))
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.status, Pedido.Status.CANCELADO)

    def test_nao_cancela_pedido_que_ja_saiu(self):
        self.pedido.status = Pedido.Status.SAIU
        self.pedido.save()
        self.client.force_login(self.loja)
        self.client.post(reverse('painel_cancelar', args=[self.pedido.pk]))
        self.pedido.refresh_from_db()
        self.assertEqual(self.pedido.status, Pedido.Status.SAIU)

    def test_fluxo_completo(self):
        self._loja_avanca()                                  # recebido
        self._loja_avanca()                                  # preparo
        self._loja_avanca(entregador=self.entregador.pk)     # saiu
        self._entregador_avanca()                            # chegou
        self._entregador_avanca()                            # entregue
        self._loja_avanca()                                  # finalizado
        self.assertEqual(self.pedido.status, Pedido.Status.FINALIZADO)

    def test_linha_do_tempo_de_pedido_cancelado_e_vazia(self):
        self.pedido.status = Pedido.Status.CANCELADO
        self.pedido.save()
        self.assertEqual(self.pedido.linha_do_tempo, [])

    def test_linha_do_tempo_marca_etapa_atual(self):
        self.pedido.status = Pedido.Status.PREPARO
        estados = [etapa['estado'] for etapa in self.pedido.linha_do_tempo]
        self.assertEqual(estados[:4], ['feito', 'feito', 'atual', 'pendente'])


# --------------------------------------------------------------------- trio
class TrioTests(BaseTestCase):
    def setUp(self):
        super().setUp()
        bebidas = Categoria.objects.create(nome='Bebidas')
        self.suco = Produto.objects.create(
            categoria=bebidas, nome='Suco Natural', preco=Decimal('7.50')
        )
        self.client.force_login(self.cliente)

    def _adicionar(self, produto, **dados):
        return self.client.post(reverse('carrinho_adicionar', args=[produto.id]), dados)

    def test_adicionar_lanche_como_trio(self):
        self._adicionar(self.burguer, trio='on')
        self.assertEqual(self.client.session['carrinho'], {f'{self.burguer.id}:trio': 1})

    def test_trio_custa_15_a_mais(self):
        self._adicionar(self.burguer, trio='on')
        resposta = self.client.get(reverse('carrinho'))
        self.assertEqual(resposta.context['subtotal'], Decimal('30.00'))   # 15 + 15
        self.assertEqual(resposta.context['total'], Decimal('37.00'))      # + 7 de taxa

    def test_bebida_nao_vira_trio(self):
        self._adicionar(self.suco, trio='on')
        self.assertEqual(self.client.session['carrinho'], {str(self.suco.id): 1})

    def test_lanche_simples_e_trio_ficam_em_linhas_separadas(self):
        self._adicionar(self.burguer)
        self._adicionar(self.burguer, trio='on')
        self.assertEqual(self.client.session['carrinho'], {
            str(self.burguer.id): 1,
            f'{self.burguer.id}:trio': 1,
        })
        resposta = self.client.get(reverse('carrinho'))
        self.assertEqual(resposta.context['subtotal'], Decimal('45.00'))   # 15 + 30

    def test_transformar_uma_unidade_em_trio(self):
        self._adicionar(self.burguer)
        self._adicionar(self.burguer)
        self.client.post(reverse('carrinho_trio', args=[self.burguer.id]), {'para': 'trio'})
        self.assertEqual(self.client.session['carrinho'], {
            str(self.burguer.id): 1,
            f'{self.burguer.id}:trio': 1,
        })

    def test_voltar_do_trio_para_so_o_lanche(self):
        self._adicionar(self.burguer, trio='on')
        self.client.post(reverse('carrinho_trio', args=[self.burguer.id]), {'para': 'simples'})
        self.assertEqual(self.client.session['carrinho'], {str(self.burguer.id): 1})

    def test_atualizar_quantidade_do_trio(self):
        self._adicionar(self.burguer, trio='on')
        self.client.post(
            reverse('carrinho_atualizar', args=[self.burguer.id]), {'quantidade': 3, 'trio': '1'}
        )
        self.assertEqual(self.client.session['carrinho'], {f'{self.burguer.id}:trio': 3})

    def test_remover_trio_nao_remove_o_lanche_simples(self):
        self._adicionar(self.burguer)
        self._adicionar(self.burguer, trio='on')
        self.client.post(reverse('carrinho_remover', args=[self.burguer.id]), {'trio': '1'})
        self.assertEqual(self.client.session['carrinho'], {str(self.burguer.id): 1})

    def test_pedido_guarda_o_trio_com_o_preco_certo(self):
        self._adicionar(self.burguer, trio='on')
        self.client.post(reverse('finalizar'), {
            'endereco_entrega': 'Rua A, 10',
            'forma_pagamento': 'pix',
        })
        pedido = Pedido.objects.get()
        item = ItemPedido.objects.get()
        self.assertTrue(item.trio)
        self.assertEqual(item.preco_unitario, Decimal('30.00'))
        self.assertEqual(pedido.subtotal, Decimal('30.00'))
        self.assertEqual(pedido.total, Decimal('37.00'))
        self.assertIn('trio', item.descricao)

    def test_desconto_de_fidelidade_considera_o_trio(self):
        for _ in range(4):
            criar_pedido(self.cliente, status=Pedido.Status.FINALIZADO)
        self._adicionar(self.burguer, trio='on')
        self.client.post(reverse('finalizar'), {
            'endereco_entrega': 'Rua A, 10',
            'forma_pagamento': 'pix',
        })
        pedido = Pedido.objects.order_by('-pk').first()
        self.assertEqual(pedido.desconto, Decimal('6.00'))   # 20% de 30
        self.assertEqual(pedido.total, Decimal('31.00'))     # 30 - 6 + 7

# Cole no FINAL de pedidos/tests.py
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
