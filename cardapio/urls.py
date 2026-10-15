from django.urls import path

from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('cardapio/', views.cardapio, name='cardapio'),
]