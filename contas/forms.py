from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Usuario


class EstiloMixin:
    """Adiciona a classe form-control do Bootstrap em todos os campos."""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for campo in self.fields.values():
            campo.widget.attrs.setdefault('class', 'form-control')


class CadastroForm(EstiloMixin, UserCreationForm):
    class Meta:
        model = Usuario
        fields = ('nome', 'email', 'telefone')


class LoginForm(EstiloMixin, AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'E-mail'