from decimal import Decimal
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image

from cardapio.models import Categoria, Produto

# As fotos originais ficam na pasta img, ao lado do manage.py
PASTA_IMAGENS = Path(settings.BASE_DIR) / 'img'
LARGURA_MAX = 900  # px: de sobra para os cards e deixa o site leve

# (nome, descrição, preço, arquivo da foto ou None)
CARDAPIO = {
    'Lanches': [
        ('X-Simples', 'Pão, blend de carne 120g e maionese da casa.', '13.00', 'x_simples.png'),
        ('X-Burguer', 'Pão, blend de carne 120g, queijo prato derretido e maionese.', '15.00', 'x_burguer.png'),
        ('X-Salada', 'Pão, blend de carne 120g, queijo, alface, tomate e maionese.', '17.00', 'x_salada.png'),
        ('X-Bacon', 'Pão, blend de carne 120g, queijo, muito bacon crocante e maionese.', '20.00', 'x_bacon.png'),
        ('X-Egg', 'Pão, blend de carne 120g, queijo, ovo frito na chapa, alface, tomate e maionese.', '18.00', 'x_egg.png'),
        ('X-Egg Bacon', 'Pão, blend de carne 120g, queijo, bacon, ovo, alface, tomate e maionese.', '22.00', 'x_egg_bacon.png'),
        ('X-Calabresa', 'Pão, blend de carne 120g, queijo, calabresa acebolada fatiada e maionese.', '19.00', 'x_calabresa.png'),
        ('X-Frango', 'Pão, filé de frango grelhado ou empanado, queijo, alface, tomate e maionese.', '18.00', 'x_frango.png'),
        ('X-Tudo da Casa', 'Pão, blend de carne 120g, salsicha, ovo, bacon, queijo, presunto, milho, batata palha, alface, tomate e maionese.', '26.00', 'x_tudo.png'),
        ('Duplo X-Burguer', 'Pão, 2x blends de carne de 120g, dobro de queijo prato e maionese.', '24.00', 'x_duplo_x_burguer.png'),

    ],
    'Bebidas': [
        ('Refrigerante Lata (350ml)', 'Opções: Coca-Cola, Fanta, Guaraná ou Pepsi.', '6.00', 'refigerante.png'),
        ('Refrigerante 2 Litros', 'Garrafa de 2 litros.', '12.00', 'refrigerante_litro.png'),
        ('Suco Natural (400ml)', 'Suco de polpa, 400ml.', '7.50',  'suco.png'),
        ('Suco Jarra Natural (1,5L)', 'Suco de polpa, 1,5 Litros.', '16.00' ,  'jarra_suco.png'),
        ('Água Mineral sem gás', 'Garrafa de água mineral sem gás.', '4.00' , 'agua.png'),
   ],
}

# (e-mail, nome, tipo, senha) - apenas para demonstração local
USUARIOS = [
    ('loja@bigbite.com', 'Loja BigBite', 'loja', 'bigbite123'),
    ('entregador@bigbite.com', 'Entregador Demo', 'entregador', 'bigbite123'),
    ('cliente@bigbite.com', 'Cliente Demo', 'cliente', 'bigbite123'),
]


def preparar_foto(caminho):
    """Reduz a foto mantendo a transparência e devolve o conteúdo em WebP."""
    with Image.open(caminho) as img:
        img = img.convert('RGBA')
        if img.width > LARGURA_MAX:
            altura = round(img.height * LARGURA_MAX / img.width)
            img = img.resize((LARGURA_MAX, altura), Image.Resampling.LANCZOS)
        buffer = BytesIO()
        img.save(buffer, format='WEBP', quality=85, method=6)
    return ContentFile(buffer.getvalue())


class Command(BaseCommand):
    help = 'Cria o cardápio padrão (com fotos) e os usuários de demonstração.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--ocultar-outros',
            action='store_true',
            help='Oculta (indisponível) os produtos que não fazem parte do cardápio padrão.',
        )
        parser.add_argument(
            '--forcar-fotos',
            action='store_true',
            help='Troca também as fotos que já existem pelas da pasta img.',
        )

    def anexar_foto(self, produto, arquivo, forcar):
        """Anexa a foto da pasta img ao produto. Devolve True se anexou."""
        if not arquivo:
            return False
        if produto.imagem and not forcar:
            return False  # mantém a foto que já está lá (ex.: enviada pelo admin)

        caminho = PASTA_IMAGENS / arquivo
        if not caminho.exists():
            self.stdout.write(self.style.WARNING(f'Foto não encontrada: {caminho}'))
            return False

        if produto.imagem:
            produto.imagem.delete(save=False)
        produto.imagem.save(f'{caminho.stem}.webp', preparar_foto(caminho), save=True)
        return True

    def handle(self, *args, **options):
        Usuario = get_user_model()
        ids_cardapio = []
        repetidos_ocultos = 0
        fotos = 0

        for ordem, (nome_categoria, itens) in enumerate(CARDAPIO.items(), start=1):
            categoria = (
                Categoria.objects.filter(nome__iexact=nome_categoria)
                .order_by('pk')
                .first()
            )
            if categoria is None:
                categoria = Categoria.objects.create(nome=nome_categoria, ordem=ordem)

            for nome, descricao, preco, foto in itens:
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

                if self.anexar_foto(produto, foto, options['forcar_fotos']):
                    fotos += 1

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
            f'Cardápio pronto: {len(ids_cardapio)} produtos, '
            f'{fotos} foto(s) anexada(s), '
            f'{repetidos_ocultos} repetido(s) ocultado(s).'
        ))