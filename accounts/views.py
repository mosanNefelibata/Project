import email
import random
import string
import time
from django.shortcuts import render, redirect, get_object_or_404
from .models import User, Message
from django.urls import reverse
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

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
    # 判断登录情况
    username = request.session.get('username')
    user_id = request.session.get('user_id')
    if username and user_id:
        return redirect(reverse('home'))

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
    # 判断登录情况
    username = request.session.get('username')
    user_id = request.session.get('user_id')
    if username and user_id:
        return redirect(reverse('home'))

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
    # 判断登录情况
    username = request.session.get('username')
    user_id = request.session.get('user_id')
    if not username or not user_id:
        return redirect(reverse('login'))

    #弹出用户名和邮箱，跳转到主页
    request.session.pop('user_id', None)
    request.session.pop('username', None)
    return redirect(reverse('home'))


def change_password(request):
    # 判断登录情况
    username = request.session.get('username')
    user_id = request.session.get('user_id')
    if not username or not user_id:
        return redirect(reverse('login'))

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
            return render(request, 'change_password.html', {'message':'Password has been changed successfully'})
    return render(request, 'change_password.html')


def change_email(request):
    # 判断登录情况
    username = request.session.get('username')
    user_id = request.session.get('user_id')
    if not username or not user_id:
        return redirect(reverse('login'))

    if request.method == 'POST':
        #判断是否需要重新发送
        if 'resend' in request.POST: 
            errors = []
            pending = request.session.get('pending_user')
            if not pending:
                errors.append('No pending email change found. Please summit a new email again.')
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
                errors.append('No pending email change found. Please try summit a new email.')
                return render(request, 'change_email.html', {'errors': errors})

            #检测验证码是否过期
            sent = pending.get('sent', 0)
            if time.time() - sent > 10 * 60:        
                request.session.pop('pending_user', None)
                errors.append('Verification code expired. Please register again.')
                return render(request, 'register.html', {'errors': errors})

            if verification_code != pending.get('code'):
                errors.append('Invalid verification code')
                return render(request, 'verify_email.html', {'errors': errors, 'email': pending.get('email')})

            #验证成功，开始修改邮箱
            user_to_update = User.objects.get(username=request.session.get('username'))
            email_addr = pending.get('email')
            if user_to_update.email==email_addr:
                errors.append('Must be different from old email address.')
                return render(request, 'change_email.html', {'errors': errors})
            
            #开始更新邮箱
            user_to_update.email = email_addr
            user_to_update.save()
            return render(request, 'verify_email.html', {'message':'Email has been changed successfully'})

        email_addr = request.POST.get('email')
        errors = []
        #检查是否填写完毕
        if not email_addr:
            errors.append('Email are required')
        #检查邮箱是否被使用
        if User.objects.filter(email=email_addr).exists():
            errors.append('Email already registered')
        if errors:
            return render(request, 'change_email.html', {'errors': errors, 'username': username, 'email': email_addr})

        #开始生成验证码
        code = ''.join(random.choices(string.digits, k=6))

        request.session['pending_user'] = {
            'username': username,
            'email': email_addr,
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
    return render(request, 'change_email.html')


def delete_account(request):
    #判断登陆情况
    username = request.session.get('username')
    user_id = request.session.get('user_id')
    if not username or not user_id:
        return redirect(reverse('login'))

    email = User.objects.get(username=username).email
    if request.method == 'POST':
        #尝试删除用户信息
        try:
            user = User.objects.get(id=user_id, username=username, email=email)
            user.delete()
        except User.DoesNotExist:
            pass
        request.session.pop('user_id', None)
        request.session.pop('username', None)
        request.session.pop('email',None)
        return render(request, 'delete_account.html', {'message': f'Your account ({email}) has been deleted.'})
    return render(request, 'delete_account.html')


def profile(request,interviewee_id):
    #判断登陆情况
    username = request.session.get('username')
    user_id = request.session.get('user_id')
    if not username or not user_id:
        return redirect(reverse('login'))
    interviewed_user = None
    privacy_setting = False
    if interviewee_id:
        try:
            interviewed_user = User.objects.get(id=interviewee_id)
            if interviewee_id != user_id:
                privacy_setting = True
        except User.DoesNotExist:
            request.session.pop('user_id', None)
            request.session.pop('username', None)
            return redirect(reverse('home'))
    else:
        return redirect(reverse('login'))
    return render(request, 'profile.html',{'user':interviewed_user , 'privacy_setting':privacy_setting})


def edit_profile(request):
    #判断登陆情况
    username = request.session.get('username')
    user_id = request.session.get('user_id')
    if not username or not user_id:
        return redirect(reverse('login'))

    user_id = request.session.get('user_id')
    username = request.session.get('username')
    if not user_id or not username:
        return redirect(reverse('login'))

    try:
        user = User.objects.get(id=user_id, username=username)
    except User.DoesNotExist:
        return redirect(reverse('login'))

    def make_context(u, extra=None):
        ctx = {
            'user': u,
            'sel_gender_M': (u.gender == 'M'),
            'sel_gender_F': (u.gender == 'F'),
            'sel_gender_S': (u.gender == 'S'),
            'sel_edu_Bachelor': (u.education == 'Bachelor'),
            'sel_edu_Master': (u.education == 'Master'),
            'sel_edu_PhD': (u.education == 'PhD'),
            'sel_edu_Other': (u.education == 'Other'),
        }
        if extra:
            ctx.update(extra)
        return ctx

    if request.method == 'POST':
        errors = []
        gender = request.POST.get('gender')
        age = request.POST.get('age')
        education = request.POST.get('education')
        school = request.POST.get('school')
        height_cm = request.POST.get('height_cm')
        weight_kg = request.POST.get('weight_kg')

        # Validate and assign
        if gender in dict(User.GENDER_CHOICES):
            user.gender = gender
        try:
            user.age = int(age) if age else None
        except ValueError:
            errors.append('Invalid age')
        if education:
            user.education = education
        if school:
            user.school = school
        try:
            user.height_cm = int(height_cm) if height_cm else None
        except ValueError:
            errors.append('Invalid height')
        try:
            user.weight_kg = int(weight_kg) if weight_kg else None
        except ValueError:
            errors.append('Invalid weight')

        # 隐私设置
        user.show_gender = True if request.POST.get('show_gender') == 'on' else False
        user.show_age = True if request.POST.get('show_age') == 'on' else False
        user.show_education = True if request.POST.get('show_education') == 'on' else False
        user.show_school = True if request.POST.get('show_school') == 'on' else False
        user.show_height = True if request.POST.get('show_height') == 'on' else False
        user.show_weight = True if request.POST.get('show_weight') == 'on' else False
        user.show_email = True if request.POST.get('show_email') == 'on' else False

        # 头像上传
        if 'avatar' in request.FILES:
            avatar = request.FILES['avatar']
            user.avatar.save(avatar.name, avatar)

        if errors:
            return render(request, 'edit_profile.html', make_context(user, {'errors': errors}))

        user.save()
        return redirect(reverse('profile'))

    return render(request, 'edit_profile.html', make_context(user))


def profile_security(request):
    #判断登陆情况
    username = request.session.get('username')
    user_id = request.session.get('user_id')
    if not username or not user_id:
        return redirect(reverse('login'))
    return render(request, 'profile_security.html')


def chats(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return redirect(reverse('login'))
    current = User.objects.get(id=user_id)
    # list other users who have exchanged messages with current
    sent_ids = set(Message.objects.filter(sender=current).values_list('receiver', flat=True))
    recv_ids = set(Message.objects.filter(receiver=current).values_list('sender', flat=True))
    other_ids = list(sent_ids.union(recv_ids))
    others = User.objects.filter(id__in=other_ids)
    # latest message preview per user, include unread count
    previews = []
    for u in others:
        last = Message.objects.filter(sender__in=[current, u], receiver__in=[current, u]).order_by('-timestamp').first()
        unread_count = Message.objects.filter(sender=u, receiver=current, is_read=False).count()
        previews.append({'user': u, 'last': last, 'unread': unread_count})
    return render(request, 'chats.html', {'previews': previews})


def chat_with(request, user_id):
    me_id = request.session.get('user_id')
    if not me_id:
        return redirect(reverse('login'))
    me = get_object_or_404(User, id=me_id)
    other = get_object_or_404(User, id=user_id)

    if request.method == 'POST':
        content = request.POST.get('content')
        if content:
            Message.objects.create(sender=me, receiver=other, content=content)
            return redirect(reverse('chat_with', args=[other.id]))

    # mark messages as read where receiver is me
    Message.objects.filter(sender=other, receiver=me, is_read=False).update(is_read=True)

    messages = Message.objects.filter(sender__in=[me, other], receiver__in=[me, other]).order_by('timestamp')
    return render(request, 'chat_with.html', {'messages': messages, 'other': other, 'me': me})


def random_match(request):
    # 随机抽取其他用户并展示资料，支持开始聊天或跳过
    me_id = request.session.get('user_id')
    if not me_id:
        return redirect(reverse('login'))
    me = get_object_or_404(User, id=me_id)

    if request.method == 'POST':
        action = request.POST.get('action')
        other_id = request.POST.get('other_id')
        if other_id:
            other = get_object_or_404(User, id=int(other_id))
            if action == 'start':
                # 创建一条初始消息以便将对方加入消息列表
                Message.objects.create(sender=me, receiver=other,content='Hi! - This is a greeting message.')
                return redirect(reverse('chat_with', args=[other.id]))
            elif action == 'skip':
                return redirect(reverse('random_match'))
    # GET 或无有效 POST 时随机抽取一个用户（排除自己）
    candidates = list(User.objects.exclude(id__in=list(Message.objects.filter(sender_id=me.id).values_list('receiver_id',flat=True)) + [me.id]))
    candidate = None
    if candidates:
        candidate = random.choice(candidates)
    return render(request, 'random_match.html', {'candidate': candidate, 'me': me})
