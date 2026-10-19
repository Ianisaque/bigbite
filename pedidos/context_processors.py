from .models import ADICIONAL_TRIO


def carrinho_quantidade(request):
    contexto = {'adicional_trio': ADICIONAL_TRIO}
    if request.user.is_authenticated:
        dados = request.session.get('carrinho', {})
        contexto['carrinho_qtd'] = sum(dados.values())
    return contexto
