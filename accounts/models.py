from django.db import models

class User(models.Model):
    GENDER_CHOICES = [
        ('M', 'Male'),
        ('F', 'Female'),
        ('S', 'Secret'),
    ]

    EDUCATION_CHOICES = [
        ('Bachelor', 'Bachelor'),
        ('Master', 'Master'),
        ('PhD', 'PhD'),
        ('Other', 'Other'),
    ]

    username = models.CharField(max_length=150, unique=True)
    email = models.EmailField(unique=True)
    password = models.CharField(max_length=128)

    # Profile fields
    gender = models.CharField(max_length=1, choices=GENDER_CHOICES, default='S')
    age = models.PositiveIntegerField(null=True, blank=True)
    education = models.CharField(max_length=20, choices=EDUCATION_CHOICES, default='Bachelor')
    school = models.CharField(max_length=200, default='Ocean University of China')
    height_cm = models.PositiveIntegerField(null=True, blank=True)
    weight_kg = models.PositiveIntegerField(null=True, blank=True)
    avatar = models.ImageField(upload_to='avatars/', null=True, blank=True)

    # Privacy settings: whether the field is visible to others
    show_gender = models.BooleanField(default=True)
    show_age = models.BooleanField(default=True)
    show_education = models.BooleanField(default=True)
    show_school = models.BooleanField(default=True)
    show_height = models.BooleanField(default=True)
    show_weight = models.BooleanField(default=True)
    show_email = models.BooleanField(default=False)

    def __str__(self):
        return self.username


class Message(models.Model):
    sender = models.ForeignKey(User, related_name='sent_messages', on_delete=models.CASCADE)
    receiver = models.ForeignKey(User, related_name='received_messages', on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    is_read = models.BooleanField(default=False)

    class Meta:
        ordering = ['timestamp']

    def __str__(self):
        return f"{self.sender} -> {self.receiver}: {self.content[:30]}"
