from datetime import timezone
import datetime
from django.db import models
from django.contrib.auth.models import AbstractBaseUser, PermissionsMixin
from .managers import UserManager

class User(AbstractBaseUser, PermissionsMixin):
    
    USER_TYPE = (
        ('Admin', 'Admin'),
        ('Customer', 'Customer'),
        ('Staff', 'Staff')
    )
    
    user_type = models.CharField(max_length=20, choices=USER_TYPE)
    profile_pic = models.ImageField(upload_to='profile/', default="profile.jpg", blank=True)
    email = models.EmailField(max_length=255, unique=True)
    first_name = models.CharField(max_length=200, verbose_name='first name')
    last_name = models.CharField(max_length=200, verbose_name='first name')
    phone_number = models.CharField(max_length=15)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)
    is_superuser = models.BooleanField(default=False)
    date_joined = models.DateTimeField(verbose_name='date joined', auto_now_add=True)
    
    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['first_name', 'last_name']    
    
    def __str__(self):
        return f"{self.first_name} {self.last_name}"

    def full_name(self):
        return f"{self.first_name} {self.last_name}"



class Contact(models.Model):
    name = models.CharField(max_length=100)
    email = models.EmailField()
    phone = models.CharField(max_length=20)
    message = models.CharField(max_length=100)

    def __str__(self):
        return self.name

class BaseModel(models.Model):
    """
    Abstract base model with common timestamp fields and soft delete capability
    """
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True, db_index=True)
    
    class Meta:
        abstract = True
        
    def soft_delete(self):
        self.is_active = False
        self.save()
       