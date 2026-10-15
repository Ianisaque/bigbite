from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from cardapio.models import Categoria, Produto

PRODUTOS = {
    'Lanches': [
        ('X-Burger', 'Pão, hambúrguer e queijo.', '18.90'),
        ('X-Bacon', 'O melhor e com muito bacon!', '26.90'),
        ('X-Tudo', 'De tudo e um pouco.', '28.99'),
    ],
    'Bebidas': [
        ('Refrigerante lata', 'Coca-cola, Fanta, Guaraná ou Pepsi.', '5.00'),
        ('Suco natural', 'Opções de acordo com a fruta do dia.', '8.00'),
    ],
}

# (e-mail, nome, tipo, senha) - apenas para demonstração local
USUARIOS = [
    ('loja@bigbite.com', 'Loja BigBite', 'loja', 'bigbite123'),
    ('entregador@bigbite.com', 'Entregador Demo', 'entregador', 'bigbite123'),
    ('cliente@bigbite.com', 'Cliente Demo', 'cliente', 'bigbite123'),
]


class Command(BaseCommand):
    help = 'Cria dados de demonstração: cardápio e usuários de teste.'

    def handle(self, *args, **options):
        Usuario = get_user_model()

        for ordem, (nome_categoria, itens) in enumerate(PRODUTOS.items(), start=1):
            categoria, _ = Categoria.objects.get_or_create(
                nome=nome_categoria, defaults={'ordem': ordem}
            )
            for nome, descricao, preco in itens:
                Produto.objects.get_or_create(
                    nome=nome,
                    categoria=categoria,
                    defaults={'descricao': descricao, 'preco': Decimal(preco)},
                )

        for email, nome, tipo, senha in USUARIOS:
            if not Usuario.objects.filter(email=email).exists():
                Usuario.objects.create_user(
                    email=email, password=senha, nome=nome, tipo=tipo
                )

        self.stdout.write(self.style.SUCCESS('Dados de demonstração criados.'))