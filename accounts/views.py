from django.shortcuts import render, redirect
from .models import User
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt


def home(request):
    user_id = request.session.get('user_id')
    user = None
    if user_id:
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            request.session.pop('user_id', None)
            request.session.pop('username', None)
    return render(request, 'home.html', {'user': user})


def register(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        email = request.POST.get('email')
        password = request.POST.get('password')
        errors = []
        if not username or not email or not password:
            errors.append('All fields are required')
        if User.objects.filter(username=username).exists():
            errors.append('Username already taken')
        if User.objects.filter(email=email).exists():
            errors.append('Email already registered')
        if not errors:
            user = User.objects.create(username=username, email=email, password=password)
            request.session['user_id'] = user.id
            request.session['username'] = user.username
            return redirect(reverse('home'))
        return render(request, 'register.html', {'errors': errors, 'username': username, 'email': email})
    return render(request, 'register.html')


def login(request):
    back_url = request.META.get('HTTP_REFERER', '/')
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        errors = []
        try:
            user = User.objects.get(username=username)
            if user.password != password:
                errors.append('Invalid credentials')
            else:
                request.session['user_id'] = user.id
                request.session['username'] = user.username
                return redirect(reverse('home'))
        except User.DoesNotExist:
            errors.append('Invalid credentials')
        return render(request, 'login.html', {'errors': errors, 'username': username, 'back_url': back_url})
    return render(request, 'login.html', {'back_url': back_url})


def logout(request):
    request.session.pop('user_id', None)
    request.session.pop('username', None)
    return redirect(reverse('home'))
