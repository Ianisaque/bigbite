from django.contrib.auth.forms import AuthenticationForm, UserCreationForm

from .models import Usuario


class CadastroForm(UserCreationForm):
    class Meta:
        model = Usuario
        fields = ('nome', 'email', 'telefone')


class LoginForm(AuthenticationForm):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['username'].label = 'E-mail'