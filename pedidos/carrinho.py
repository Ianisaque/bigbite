from decimal import Decimal

from cardapio.models import Produto

from .models import ADICIONAL_TRIO, TAXA_ENTREGA

SESSION_KEY = 'carrinho'
SUFIXO_TRIO = ':trio'
OBS_KEY = 'observacao'


def chave_do_item(produto_id, trio=False):
    """Lanche simples: '12'. Lanche em trio: '12:trio' (linha separada no carrinho)."""
    return f'{produto_id}{SUFIXO_TRIO}' if trio else str(produto_id)


class Carrinho:
    def __init__(self, request):
        self.session = request.session
        self.dados = self.session.setdefault(SESSION_KEY, {})

    def _salvar(self):
        self.session.modified = True

    def adicionar(self, produto_id, quantidade=1, trio=False):
        chave = chave_do_item(produto_id, trio)
        self.dados[chave] = self.dados.get(chave, 0) + quantidade
        self._salvar()

    def definir(self, produto_id, quantidade, trio=False):
        chave = chave_do_item(produto_id, trio)
        if quantidade <= 0:
            self.dados.pop(chave, None)
        else:
            self.dados[chave] = quantidade
        self._salvar()

    def remover(self, produto_id, trio=False):
        self.dados.pop(chave_do_item(produto_id, trio), None)
        self._salvar()

    def converter(self, produto_id, para_trio):
        """Passa UMA unidade do lanche simples para trio (ou de volta)."""
        origem = chave_do_item(produto_id, not para_trio)
        destino = chave_do_item(produto_id, para_trio)
        if self.dados.get(origem, 0) <= 0:
            return
        self.dados[origem] -= 1
        if self.dados[origem] <= 0:
            del self.dados[origem]
        self.dados[destino] = self.dados.get(destino, 0) + 1
        self._salvar()

    def limpar(self):
        self.session[SESSION_KEY] = {}
        self.session.pop(OBS_KEY, None)
        self._salvar()

    def resumo(self, cliente=None):
        ids = {int(chave.split(':')[0]) for chave in self.dados}
        produtos = {
            p.id: p
            for p in Produto.objects.select_related('categoria').filter(id__in=ids, disponivel=True)
        }

        itens = []
        for chave, quantidade in self.dados.items():
            id_texto, _, sufixo = chave.partition(':')
            trio = sufixo == 'trio'
            produto = produtos.get(int(id_texto))
            if produto is None or (trio and not produto.permite_trio):
                continue

            preco_unitario = produto.preco + (ADICIONAL_TRIO if trio else Decimal('0'))
            itens.append({
                'produto': produto,
                'quantidade': quantidade,
                'trio': trio,
                'preco_unitario': preco_unitario,
                'subtotal': preco_unitario * quantidade,
                'descricao': f'{produto.nome} em trio (+ batata e refri lata)' if trio else produto.nome,
            })
        itens.sort(key=lambda i: (i['produto'].categoria_id, i['produto'].nome, i['trio']))

        subtotal = sum((i['subtotal'] for i in itens), Decimal('0'))

        desconto = Decimal('0')
        posicao = None
        if cliente is not None:
            from .fidelidade import calcular_desconto, posicao_no_ciclo, tem_desconto
            posicao = posicao_no_ciclo(cliente)
            if tem_desconto(cliente):
                desconto = calcular_desconto(subtotal)

        return {
            'itens': itens,
            'subtotal': subtotal,
            'desconto': desconto,
            'fidelidade': desconto > 0,
            'posicao_fidelidade': posicao,
            'taxa_entrega': TAXA_ENTREGA,
            'adicional_trio': ADICIONAL_TRIO,
            'total': subtotal - desconto + TAXA_ENTREGA,
        }

    @property
    def observacao(self):
        return self.session.get(OBS_KEY, '')

    def definir_observacao(self, texto):
        self.session[OBS_KEY] = (texto or '').strip()[:300]
        self._salvar()