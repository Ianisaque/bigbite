def carrinho_quantidade(request):
    if not request.user.is_authenticated:
        return {}
    dados = request.session.get('carrinho', {})
    return {'carrinho_qtd': sum(dados.values())}