from django.urls import path
from . import views

urlpatterns = [
    path('', views.home, name='home'),
    path('register/', views.register, name='register'),
    path('login/', views.login, name='login'),
    path('logout/', views.logout, name='logout'),
    path('profile/<int:interviewee_id>', views.profile, name='profile'),
    path('profile/edit/', views.edit_profile, name='edit_profile'),
    path('profile/security/', views.profile_security, name='profile_security'),
    path('change_password/',views.change_password, name='change_password'),
    path('change_email/', views.change_email, name='change_email'),
    path('delete_account/', views.delete_account, name='delete_account'),
    path('chat/', views.chats, name='chats'),
    path('chat/<int:user_id>/', views.chat_with, name='chat_with'),
    path('random_match/', views.random_match, name='random_match'),
]

