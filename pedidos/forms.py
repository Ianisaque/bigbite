from django import forms

from .models import Pedido


class CheckoutForm(forms.ModelForm):
    forma_pagamento = forms.ChoiceField(
        label='Forma de pagamento',
        choices=Pedido.Pagamento.choices,
        widget=forms.RadioSelect,
    )

    class Meta:
        model = Pedido
        fields = ('endereco_entrega', 'forma_pagamento')
        labels = {'endereco_entrega': 'Endereço de entrega'}
        widgets = {
            'endereco_entrega': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'Rua, número, bairro, complemento',
            }),
        }