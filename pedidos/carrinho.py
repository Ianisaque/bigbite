from .fidelidade import calcular_desconto, posicao_no_ciclo, tem_desconto

from decimal import Decimal

from cardapio.models import Produto

from .models import TAXA_ENTREGA

SESSION_KEY = 'carrinho'


class Carrinho:
    def __init__(self, request):
        self.session = request.session
        self.dados = self.session.setdefault(SESSION_KEY, {})

    def _salvar(self):
        self.session.modified = True

    def adicionar(self, produto_id, quantidade=1):
        chave = str(produto_id)
        self.dados[chave] = self.dados.get(chave, 0) + quantidade
        self._salvar()

    def definir(self, produto_id, quantidade):
        chave = str(produto_id)
        if quantidade <= 0:
            self.dados.pop(chave, None)
        else:
            self.dados[chave] = quantidade
        self._salvar()

    def remover(self, produto_id):
        self.dados.pop(str(produto_id), None)
        self._salvar()

    def limpar(self):
        self.session[SESSION_KEY] = {}
        self._salvar()

    def resumo(self, cliente=None):
        produtos = Produto.objects.filter(id__in=self.dados.keys(), disponivel=True)
        itens = []
        for produto in produtos:
            quantidade = self.dados[str(produto.id)]
            itens.append({
                'produto': produto,
                'quantidade': quantidade,
                'subtotal': produto.preco * quantidade,
            })

        subtotal = sum((i['subtotal'] for i in itens), Decimal('0'))

        desconto = Decimal('0')
        posicao = None
        if cliente is not None:
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
            'total': subtotal - desconto + TAXA_ENTREGA,
        }