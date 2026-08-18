from django import forms

from .models import TicketType


class TicketTypeForm(forms.ModelForm):
    class Meta:
        model = TicketType
        fields = ("name", "price", "quantity_total")


class AddToCartForm(forms.Form):
    ticket_type = forms.ModelChoiceField(
        queryset=TicketType.objects.all(),
        error_messages={"invalid_choice": "Invalid ticket tier."},
    )
    quantity = forms.IntegerField(min_value=1)