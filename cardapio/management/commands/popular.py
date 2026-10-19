from decimal import Decimal
from io import BytesIO
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from PIL import Image

from cardapio.models import Categoria, Produto

# As fotos originais ficam em static/img (ou, se não houver, na pasta img ao lado do manage.py)
PASTAS_IMAGENS = [Path(settings.BASE_DIR) / 'static' / 'img', Path(settings.BASE_DIR) / 'img']
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
    'Porções': [
        ('Batata Frita (300g)', 'Serve 1 a 2 pessoas. Batata frita crocante, temperada com sal e ervas.', '16.00', 'batata.png'),
        ('Batata com Cheddar e Bacon (350g)', 'Serve 1 a 2 pessoas. Batata frita com cheddar cremoso e bacon crocante.', '24.00', 'batata_cheddar_bacon.png'),
        ('Onion Rings (10 unid.)', 'Serve 1 a 2 pessoas. Cerca de 200g de anéis de cebola empanados e crocantes.', '20.00', 'onion_rings.png'),
    ],
    'Bebidas': [
        ('Refrigerante Lata (350ml)', 'Opções: Coca-Cola, Fanta, Guaraná ou Pepsi.', '6.00', 'refigerante.png'),
        ('Refrigerante 2 Litros', 'Garrafa de 2 litros.', '12.00', 'refrigerante_litro.png'),
        ('Suco Natural (400ml)', 'Suco de polpa, 400ml.', '7.50',  'suco.png'),
        ('Suco Jarra Natural (1,5L)', 'Suco de polpa, 1,5 Litros.', '16.00' ,  'jarra_suco.png'),
        ('Água Mineral sem gás', 'Garrafa de água mineral sem gás.', '4.00' , 'agua.png'),
        ('Milk Shake de Morango (400ml)', 'Milk shake cremoso de morango com chantilly e cereja.', '14.00', 'milkshake_morango.png'),
        ('Milk Shake de Creme (400ml)', 'Milk shake cremoso de baunilha com chantilly e cereja.', '14.00', 'milkshake_creme.png'),
        ('Milk Shake de Chocolate (400ml)', 'Milk shake cremoso de chocolate com chantilly e cereja.', '14.00', 'milkshake_chocolate.png'),
   ],
}

# (e-mail, nome, tipo, senha) - apenas para demonstração local
USUARIOS = [
    ('loja@bigbite.com', 'Loja BigBite', 'loja', 'bigbite123'),
    ('entregador@bigbite.com', 'Entregador Demo', 'entregador', 'bigbite123'),
    ('cliente@bigbite.com', 'Cliente Demo', 'cliente', 'bigbite123'),
]


def preparar_foto(caminho):
    """Reduz a foto mantendo a transparência. Devolve (conteúdo, extensão).

    Tenta WebP (leve) com qualidades decrescentes; se o WebP falhar no seu
    computador, grava um PNG otimizado em vez de parar o comando.
    """
    with Image.open(caminho) as img:
        img = img.convert('RGBA')
        if img.width > LARGURA_MAX:
            altura = round(img.height * LARGURA_MAX / img.width)
            img = img.resize((LARGURA_MAX, altura), Image.Resampling.LANCZOS)

    for qualidade, metodo in ((85, 6), (80, 4), (75, 4), (70, 0)):
        try:
            buffer = BytesIO()
            img.save(buffer, format='WEBP', quality=qualidade, method=metodo)
            return ContentFile(buffer.getvalue()), 'webp'
        except Exception:
            continue

    buffer = BytesIO()
    img.save(buffer, format='PNG', optimize=True)
    return ContentFile(buffer.getvalue()), 'png'


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
            help='Troca também as fotos que já existem pelas de static/img.',
        )

    def anexar_foto(self, produto, arquivo, forcar):
        """Anexa a foto da pasta img ao produto. Devolve True se anexou."""
        if not arquivo:
            return False
        if produto.imagem and not forcar:
            return False  # mantém a foto que já está lá (ex.: enviada pelo admin)

        caminho = next((p / arquivo for p in PASTAS_IMAGENS if (p / arquivo).exists()), None)
        if caminho is None:
            self.stdout.write(self.style.WARNING(f'Foto não encontrada: {arquivo} (procurei em static/img e img)'))
            return False

        if produto.imagem:
            produto.imagem.delete(save=False)
        conteudo, extensao = preparar_foto(caminho)
        if extensao != 'webp':
            self.stdout.write(self.style.WARNING(f'{arquivo}: WebP falhou, usando PNG.'))
        produto.imagem.save(f'{caminho.stem}.{extensao}', conteudo, save=True)
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
            elif categoria.ordem != ordem:
                categoria.ordem = ordem
                categoria.save(update_fields=['ordem'])

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