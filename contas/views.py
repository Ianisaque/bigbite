from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import CadastroForm, LoginForm


class EntrarView(LoginView):
    template_name = 'contas/login.html'
    authentication_form = LoginForm
    redirect_authenticated_user = True

    def form_valid(self, form):
        resposta = super().form_valid(form)
        messages.success(self.request, f'Bem-vindo de volta, {form.get_user().nome}!')
        return resposta

    def get_success_url(self):
        destino = self.get_redirect_url()  # ?next=... tem prioridade
        if destino:
            return destino
        tipo = self.request.user.tipo
        if tipo == 'loja':
            return reverse('painel')
        if tipo == 'entregador':
            return reverse('entregas')
        return reverse('home')


def cadastro(request):
    if request.user.is_authenticated:
        return redirect('home')

    form = CadastroForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        usuario = form.save()
        login(request, usuario)
        messages.success(request, f'Conta criada! Bem-vindo ao BigBite, {usuario.nome}.')
        return redirect('home')

    return render(request, 'contas/cadastro.html', {'form': form})