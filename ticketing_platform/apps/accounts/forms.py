from django import forms
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm

from .models import Profile

User = get_user_model()


class SignupForm(UserCreationForm):
    role = forms.ChoiceField(
        choices=Profile.Role.choices,
        initial=Profile.Role.ATTENDEE,
        label="I am signing up as",
    )

    class Meta:
        model = User
        fields = ("username", "email")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["email"].required = True