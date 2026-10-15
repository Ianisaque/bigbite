from django.db.models import Prefetch
from django.shortcuts import render

from .models import Categoria, Produto


def _categorias():
    disponiveis = Produto.objects.filter(disponivel=True)
    return Categoria.objects.prefetch_related(
        Prefetch('produtos', queryset=disponiveis)
    )


def home(request):
    return render(request, 'cardapio/home.html', {'categorias': _categorias()})


def cardapio(request):
    return render(request, 'cardapio/cardapio.html', {'categorias': _categorias()})