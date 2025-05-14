from django.db import models
from django.forms import ValidationError
from django.contrib.auth.models import AbstractUser

class User(AbstractUser):
    USER_TYPE_CHOICES = (
        ('admin', 'Admin'),
        ('developer', 'Developer'),
    )
    
    user_type = models.CharField(
        max_length=10,
        choices=USER_TYPE_CHOICES,
        default='developer'
    )  
    profile_photo = models.ImageField(
        upload_to='profile_photos/',
        null=True,
        blank=True
    ) 

class Framework(models.Model):
    TYPE_CHOICES = (
        ('Frontend', 'Frontend'),
        ('Backend', 'Backend'),
    )
    name = models.CharField(max_length=255, unique=True)
    logo = models.ImageField(upload_to='frameworks/logos/', null=True, blank=True)
    short_description = models.TextField(null=True, blank=True)
    type = models.CharField(max_length=10, choices=TYPE_CHOICES, default='Backend')  # Added default
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return self.name
   
def project_script_upload_path(instance, filename):
    # File will be uploaded to MEDIA_ROOT/projects/user_<id>/<filename>
    return f'projects/user_{instance.user.id}/{filename}'
    
class Project(models.Model):
    project_name = models.CharField(max_length=255)
    # Change from selected_tables to tables
    tables = models.JSONField(default=list)
    framework = models.ForeignKey('Framework', on_delete=models.CASCADE, related_name='projects')
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='projects', null=True)
    date_creation = models.DateTimeField(auto_now_add=True)
    date_modification = models.DateTimeField(auto_now=True)
    script_file = models.FileField(
        upload_to=project_script_upload_path, 
        null=True, 
        blank=True, 
        help_text="Upload a script file for project creation"
    )
    zip_file = models.FileField(upload_to='zips/', null=True, blank=True)
    
    def __str__(self):
        return self.project_name


