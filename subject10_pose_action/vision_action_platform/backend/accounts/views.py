"""회원가입만 직접 작성. 로그인·로그아웃은 Django 기본 뷰를 쓴다 (accounts/urls.py)."""
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm
from django.shortcuts import redirect, render


def signup(request):
    if request.user.is_authenticated:
        return redirect("analyses:index")
    form = UserCreationForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user)
        return redirect("analyses:index")
    return render(request, "accounts/signup.html", {"form": form})
