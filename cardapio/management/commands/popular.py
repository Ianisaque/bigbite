from decimal import Decimal

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from cardapio.models import Categoria, Produto

# (nome, descrição, preço)
CARDAPIO = {
    'Lanches': [
        ('Hambúrguer Simples', 'Pão, blend de carne 120g e maionese da casa.', '13.00'),
        ('X-Burguer', 'Pão, blend de carne 120g, queijo prato derretido e maionese.', '15.00'),
        ('X-Salada', 'Pão, blend de carne 120g, queijo, alface, tomate e maionese.', '17.00'),
        ('X-Bacon', 'Pão, blend de carne 120g, queijo, muito bacon crocante e maionese.', '20.00'),
        ('X-Egg', 'Pão, blend de carne 120g, queijo, ovo frito na chapa, alface, tomate e maionese.', '18.00'),
        ('X-Egg Bacon', 'Pão, blend de carne 120g, queijo, bacon, ovo, alface, tomate e maionese.', '22.00'),
        ('X-Calabresa', 'Pão, blend de carne 120g, queijo, calabresa acebolada fatiada e maionese.', '19.00'),
        ('X-Frango', 'Pão, filé de frango grelhado ou empanado, queijo, alface, tomate e maionese.', '18.00'),
        ('X-Tudo da Casa', 'Pão, blend de carne 120g, salsicha, ovo, bacon, queijo, presunto, milho, batata palha, alface, tomate e maionese.', '26.00'),
        ('Duplo X-Burguer', 'Pão, 2x blends de carne de 120g, dobro de queijo prato e maionese.', '24.00'),
    ],
    'Bebidas': [
        ('Refrigerante Lata (350ml)', 'Opções: Coca-Cola, Fanta, Guaraná ou Pepsi.', '6.00'),
        ('Refrigerante 2 Litros', 'Garrafa de 2 litros.', '12.00'),
        ('Suco Natural (400ml)', 'Suco de polpa, 400ml.', '7.50'),
        ('Água Mineral sem gás', 'Garrafa de água mineral sem gás.', '4.00'),
        ('Água Mineral com gás', 'Garrafa de água mineral com gás.', '4.50'),
        ('Cerveja Latão (473ml)', 'Lata de 473ml.', '7.00'),
    ],
}

# (e-mail, nome, tipo, senha) - apenas para demonstração local
USUARIOS = [
    ('loja@bigbite.com', 'Loja BigBite', 'loja', 'bigbite123'),
    ('entregador@bigbite.com', 'Entregador Demo', 'entregador', 'bigbite123'),
    ('cliente@bigbite.com', 'Cliente Demo', 'cliente', 'bigbite123'),
]


class Command(BaseCommand):
    help = 'Cria o cardápio padrão e os usuários de demonstração.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ocultar-outros',
            action='store_true',
            help='Oculta (indisponível) os produtos que não fazem parte do cardápio padrão.',
        )

    def handle(self, *args, **options):
        Usuario = get_user_model()
        ids_cardapio = []
        repetidos_ocultos = 0

        for ordem, (nome_categoria, itens) in enumerate(CARDAPIO.items(), start=1):
            categoria = (
                Categoria.objects.filter(nome__iexact=nome_categoria)
                .order_by('pk')
                .first()
            )
            if categoria is None:
                categoria = Categoria.objects.create(nome=nome_categoria, ordem=ordem)

            for nome, descricao, preco in itens:
                existentes = list(
                    Produto.objects.filter(categoria=categoria, nome__iexact=nome)
                    .order_by('pk')
                )
                # se houver repetidos, mantém o que já tem foto (senão, o mais antigo)
                existentes.sort(key=lambda p: not p.imagem)

                if existentes:
                    produto = existentes[0]
                    produto.nome = nome
                    produto.descricao = descricao
                    produto.preco = Decimal(preco)
                    produto.disponivel = True
                    produto.save()

                    for repetido in existentes[1:]:
                        repetido.disponivel = False
                        repetido.save(update_fields=['disponivel'])
                        repetidos_ocultos += 1
                else:
                    produto = Produto.objects.create(
                        categoria=categoria,
                        nome=nome,
                        descricao=descricao,
                        preco=Decimal(preco),
                    )

                ids_cardapio.append(produto.pk)

        if options['ocultar_outros']:
            ocultos = Produto.objects.exclude(pk__in=ids_cardapio).update(disponivel=False)
            self.stdout.write(f'{ocultos} produto(s) fora do cardápio padrão foram ocultados.')

        for email, nome, tipo, senha in USUARIOS:
            if not Usuario.objects.filter(email=email).exists():
                Usuario.objects.create_user(
                    email=email, password=senha, nome=nome, tipo=tipo
                )

        self.stdout.write(self.style.SUCCESS(
            f'Cardápio pronto: {len(ids_cardapio)} produtos '
            f'({repetidos_ocultos} repetido(s) ocultado(s)).'
        ))