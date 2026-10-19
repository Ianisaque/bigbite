from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

Usuario = get_user_model()
SENHA = 'Senha-Forte-9137'


class LoginTests(TestCase):
    def _criar(self, email, tipo):
        return Usuario.objects.create_user(email=email, password=SENHA, nome='Teste', tipo=tipo)

    def _entrar(self, email, senha=SENHA, **extra):
        return self.client.post(reverse('login'), {'username': email, 'password': senha, **extra})

    def test_cliente_vai_para_a_home(self):
        self._criar('c@teste.com', 'cliente')
        resposta = self._entrar('c@teste.com')
        self.assertRedirects(resposta, reverse('home'), fetch_redirect_response=False)

    def test_loja_vai_para_o_painel(self):
        self._criar('l@teste.com', 'loja')
        resposta = self._entrar('l@teste.com')
        self.assertRedirects(resposta, reverse('painel'), fetch_redirect_response=False)

    def test_entregador_vai_para_as_entregas(self):
        self._criar('e@teste.com', 'entregador')
        resposta = self._entrar('e@teste.com')
        self.assertRedirects(resposta, reverse('entregas'), fetch_redirect_response=False)

    def test_next_tem_prioridade(self):
        self._criar('c@teste.com', 'cliente')
        resposta = self._entrar('c@teste.com', next=reverse('carrinho'))
        self.assertRedirects(resposta, reverse('carrinho'), fetch_redirect_response=False)

    def test_senha_errada_nao_entra(self):
        self._criar('c@teste.com', 'cliente')
        resposta = self._entrar('c@teste.com', senha='errada')
        self.assertEqual(resposta.status_code, 200)
        self.assertNotIn('_auth_user_id', self.client.session)

    def test_sair_encerra_a_sessao(self):
        usuario = self._criar('c@teste.com', 'cliente')
        self.client.force_login(usuario)
        self.client.post(reverse('logout'))
        self.assertNotIn('_auth_user_id', self.client.session)


class CadastroTests(TestCase):
    dados = {
        'nome': 'Maria',
        'email': 'maria@teste.com',
        'telefone': '61999999999',
        'password1': SENHA,
        'password2': SENHA,
    }

    def test_cadastro_cria_cliente_e_ja_loga(self):
        resposta = self.client.post(reverse('cadastro'), self.dados)
        self.assertRedirects(resposta, reverse('home'), fetch_redirect_response=False)
        usuario = Usuario.objects.get(email='maria@teste.com')
        self.assertEqual(usuario.tipo, 'cliente')
        self.assertEqual(int(self.client.session['_auth_user_id']), usuario.pk)

    def test_nao_da_para_se_cadastrar_como_loja(self):
        self.client.post(reverse('cadastro'), {**self.dados, 'tipo': 'loja', 'is_staff': 'on'})
        usuario = Usuario.objects.get(email='maria@teste.com')
        self.assertEqual(usuario.tipo, 'cliente')
        self.assertFalse(usuario.is_staff)

    def test_email_duplicado_e_recusado(self):
        Usuario.objects.create_user(email='maria@teste.com', password=SENHA, nome='Outra')
        resposta = self.client.post(reverse('cadastro'), self.dados)
        self.assertEqual(resposta.status_code, 200)
        self.assertEqual(Usuario.objects.filter(email='maria@teste.com').count(), 1)

    def test_senhas_diferentes_sao_recusadas(self):
        resposta = self.client.post(reverse('cadastro'), {**self.dados, 'password2': 'outra-coisa-123'})
        self.assertEqual(resposta.status_code, 200)
        self.assertFalse(Usuario.objects.filter(email='maria@teste.com').exists())

    def test_logado_e_redirecionado_do_cadastro(self):
        usuario = Usuario.objects.create_user(email='a@teste.com', password=SENHA, nome='A')
        self.client.force_login(usuario)
        resposta = self.client.get(reverse('cadastro'))
        self.assertRedirects(resposta, reverse('home'), fetch_redirect_response=False)
