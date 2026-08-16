from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.views import LoginView
from django.shortcuts import redirect, render

from .forms import SignupForm


class UserLoginView(LoginView):
    template_name = "accounts/login.html"


def signup(request):
    if request.user.is_authenticated:
        return redirect("events:home")
    if request.method == "POST":
        form = SignupForm(request.POST)
        if form.is_valid():
            user = form.save()
            user.profile.role = form.cleaned_data["role"]
            user.profile.save()
            login(request, user)
            messages.success(request, f"Welcome, {user.username}!")
            return redirect("events:home")
    else:
        form = SignupForm()
    return render(request, "accounts/signup.html", {"form": form})