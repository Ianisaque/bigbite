from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


class UsuarioManager(BaseUserManager):
    def create_user(self, email, password=None, **extra):
        if not email:
            raise ValueError('O e-mail é obrigatório')
        email = self.normalize_email(email)
        user = self.model(email=email, **extra)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra):
        extra.setdefault('is_staff', True)
        extra.setdefault('is_superuser', True)
        extra.setdefault('tipo', 'loja')
        return self.create_user(email, password, **extra)


class Usuario(AbstractUser):
    TIPOS = [
        ('cliente', 'Cliente'),
        ('loja', 'Loja'),
        ('entregador', 'Entregador'),
    ]

    username = None
    email = models.EmailField('e-mail', unique=True)
    nome = models.CharField(max_length=100)
    telefone = models.CharField(max_length=20, blank=True)
    tipo = models.CharField(max_length=10, choices=TIPOS, default='cliente')

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['nome']

    objects = UsuarioManager()

    def __str__(self):
        return self.email