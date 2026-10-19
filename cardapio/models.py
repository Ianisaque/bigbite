from django.db import models


class Categoria(models.Model):
    nome = models.CharField(max_length=50)
    ordem = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ['ordem', 'nome']

    def __str__(self):
        return self.nome


class Produto(models.Model):
    categoria = models.ForeignKey(
        Categoria, on_delete=models.PROTECT, related_name='produtos'
    )
    nome = models.CharField(max_length=100)
    descricao = models.TextField(blank=True)
    preco = models.DecimalField(max_digits=8, decimal_places=2)
    imagem = models.ImageField(upload_to='produtos/', blank=True)
    disponivel = models.BooleanField(default=True)
    
    @property
    def permite_trio(self):
        """Só os lanches podem virar trio."""
        return self.categoria.nome.strip().lower() == 'lanches'

    class Meta:
        ordering = ['categoria', 'nome']

    def __str__(self):
        return self.nome