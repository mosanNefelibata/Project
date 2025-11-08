from django.shortcuts import render, redirect
from .models import User
from django.urls import reverse
import random
import string
import time
from django.core.mail import send_mail
from django.conf import settings


def home(request):
    user_id = request.session.get('user_id')
    user = None
    if user_id:
        try:
            user = User.objects.get(id=user_id)
        except User.DoesNotExist:
            request.session.pop('user_id', None)
            request.session.pop('username', None)
            return redirect(reverse('home'))
    return render(request, 'home.html', {'user': user})


def register(request):
    if request.method == 'POST':
        #判断是否需要重新发送
        if 'resend' in request.POST: 
            errors = []
            pending = request.session.get('pending_user')
            if not pending:
                errors.append('No pending registration found. Please try registering again.')
                return render(request, 'register.html', {'errors': errors})

            code = ''.join(random.choices(string.digits, k=6))
            pending['code'] = code
            pending['sent'] = time.time()
            request.session['pending_user'] = pending

            email_addr = pending.get('email')
            subject = 'Your verification code'
            message = f'Your verification code is: {code}'
            from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)

            #尝试发送验证码，否则在终端打印
            try:                
                send_mail(subject, message, from_email, [email_addr])
                mailed = True
            except Exception:
                print(f'Failed to send email. Verification code for {email_addr}: {code}')
                mailed = False

            return render(request, 'verify_email.html', {'email': email_addr, 'mailed': mailed, 'message': 'Verification code resent.'})

        verification_code = request.POST.get('verification_code')
        if verification_code is not None:
            errors = []
            pending = request.session.get('pending_user')
            if not pending:
                errors.append('No pending registration found. Please try registering again.')
                return render(request, 'register.html', {'errors': errors})

            #检测验证码是否过期
            sent = pending.get('sent', 0)
            if time.time() - sent > 10 * 60:        
                request.session.pop('pending_user', None)
                errors.append('Verification code expired. Please register again.')
                return render(request, 'register.html', {'errors': errors})

            if verification_code != pending.get('code'):
                errors.append('Invalid verification code')
                return render(request, 'verify_email.html', {'errors': errors, 'email': pending.get('email')})

            #验证成功，开始创建用户
            username = pending.get('username')
            email_addr = pending.get('email')
            password = pending.get('password')
            user = User.objects.create(username=username, email=email_addr, password=password)

            request.session.pop('pending_user', None)
            request.session['user_id'] = user.id
            request.session['username'] = user.username
            return render(request, 'verify_email.html', {'message':'Register successfully'})

        username = request.POST.get('username')
        email_addr = request.POST.get('email')
        password = request.POST.get('password')
        errors = []
        #检查是否填写完毕
        if not username or not email_addr or not password:
            errors.append('All fields are required')
        #检查用户名和邮箱是否被使用
        if User.objects.filter(username=username).exists():
            errors.append('Username already taken')
        if User.objects.filter(email=email_addr).exists():
            errors.append('Email already registered')
        if errors:
            return render(request, 'register.html', {'errors': errors, 'username': username, 'email': email_addr})

        #开始生成验证码
        code = ''.join(random.choices(string.digits, k=6))

        request.session['pending_user'] = {
            'username': username,
            'email': email_addr,
            'password': password,
            'code': code,
            'sent': time.time()
        }

        #尝试发送验证码，否则在终端打印
        subject = 'Your verification code'
        message = f'Your verification code is: {code}'
        from_email = getattr(settings, 'DEFAULT_FROM_EMAIL', None)
        try:
            send_mail(subject, message, from_email, [email_addr])
            mailed = True
        except Exception:
            print(f'Failed to send email. Verification code for {email_addr}: {code}')
            mailed = False

        return render(request, 'verify_email.html', {'email': email_addr, 'mailed': mailed})
    return render(request, 'register.html')


def login(request):
        #检查是否提交用户名和密码
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        errors = []
        #尝试登陆
        try:
            user = User.objects.get(username=username)
            if user.password != password:
                errors.append('Incorrect password')
            else:
                #成功登录则跳转到主页
                request.session['user_id'] = user.id
                request.session['username'] = user.username
                return redirect(reverse('home'))
        except User.DoesNotExist:
            errors.append('User does not exist')
        return render(request, 'login.html', {'errors': errors, 'username': username })
    return render(request, 'login.html')


def logout(request):
    #弹出用户名和邮箱，跳转到主页
    request.session.pop('user_id', None)
    request.session.pop('username', None)
    return redirect(reverse('home'))


def change_password(request):
    #检查是否提交密码
    if request.method == 'POST':
        errors = []
        password1 = request.POST.get('password1')
        password2 = request.POST.get('password2')
        #开始检查新密码合法性
        if password1 != password2:
            errors.append('Passwords do not match')
            return render(request, 'change_password.html', {'errors': errors})
        else:
            user_to_update = User.objects.get(username=request.session.get('username'))
            if user_to_update.password == password1:
                errors.append('Must be different from old password.')
                return render(request, 'change_password.html', {'errors': errors})
            
            #开始更新密码
            user_to_update.password = password1
            user_to_update.save()
            return render(request, 'change_password.html', {'message':'Password changed successfully'})
    return render(request, 'change_password.html')


def change_email(request):
    #检查是否提交新密码
    if request.method == 'POST':
        errors = []
        new_email = request.POST.get('email')
        #检查邮箱是否被使用
        if User.objects.filter(email=new_email).exists():
            errors.append('This email address is already in use.')
            return render(request,'change_email.html',{ 'errors' : errors})
        user_to_update = User.objects.get(username=request.session.get('username'))
        if user_to_update.email == new_email:
            errors.append('Must be different from old email.')
            return render(request, 'change_email.html', {'errors': errors})
        #开始修改邮箱
        user_to_update.email = new_email
        user_to_update.save()
        return render(request, 'change_email.html', {'message':'Email changed successfully'})
    return render(request, 'change_email.html')


def delete_account(request):
    #获取当前用户名和ID
    username = request.session.get('username')
    user_id = request.session.get('user_id')
    if not username or not user_id:
        return redirect(reverse('login'))

    if request.method == 'POST':
        #尝试删除用户信息
        try:
            user = User.objects.get(id=user_id, username=username)
            user.delete()
        except User.DoesNotExist:
            pass
        request.session.pop('user_id', None)
        request.session.pop('username', None)
        return render(request, 'delete_account.html', {'message': 'Your account has been deleted.'})
    return render(request, 'delete_account.html')
