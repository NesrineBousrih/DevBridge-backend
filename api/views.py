import os
from django.conf import settings
from django.core.files.base import ContentFile
from rest_framework import viewsets
from .models import  Project, Framework
from .serializers import  ProjectCreateSerializer, ProjectSerializer, UserSerializer,FrameworkSerializer
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from django.contrib.auth.models import User
from rest_framework.permissions import IsAuthenticated

class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        user = User.objects.get(username=response.data['username'])
        token, created = Token.objects.get_or_create(user=user)
        return Response({'token': token.key})

class UserLoginView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request):
        username = request.data.get('username')
        password = request.data.get('password')

        if not username or not password:
            return Response({'error': 'Username and password required'}, status=400)

        user = authenticate(username=username, password=password)
        if user:
            token, created = Token.objects.get_or_create(user=user)
            return Response({'token': token.key})
        return Response({'error': 'Invalid credentials'}, status=401)
    
    
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response(serializer.data)

class FrameworkViewSet(viewsets.ModelViewSet):
    queryset = Framework.objects.all()
    serializer_class = FrameworkSerializer
    
    def get_queryset(self):
        queryset = Framework.objects.all()
        framework_type = self.request.query_params.get('type', None)
        
        if framework_type:
            queryset = queryset.filter(type=framework_type)
        
        return queryset
    
    


class ProjectViewSet(viewsets.ModelViewSet):
    queryset = Project.objects.all()
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ProjectCreateSerializer
        return ProjectSerializer
    
    def perform_create(self, serializer):
        # Set the user to the current user if not specified
        if 'user' not in serializer.validated_data:
            serializer.validated_data['user'] = self.request.user
        
        # Let the serializer's create method handle creating the project and fields
        project = serializer.save()
        
        # Now generate the script after the project and fields are created
        self._generate_and_attach_script(project)
        
        return project
    
    def _generate_and_attach_script(self, project):
        """Generate the shell script content and attach it to the project"""
        app_name = project.project_name.lower()
        model_name = project.model_name.lower()
        
        # Get fields from the related Field objects
        fields = project.fields.all()
        field_names = [field.name for field in fields]

        # Generate the script content
        script_content = self._generate_script_content(app_name, model_name, field_names,project.framework.name)
        
        # Create a file object to attach to the model
        script_file = ContentFile(script_content.encode('utf-8'))
        
        # Generate a filename based on the project
        filename = f"init_{project.id}_{app_name}_{model_name}.sh"
        
        # Update with the file
        project.script_file.save(filename, script_file, save=True)
    
    def _generate_script_content(self, app_name, model_name, field_names ,framework="Angular"):
        
        """Generate the shell script content with the appropriate parameters
            
             Args:
        app_name: The name of the app
        model_name: The name of the model
        field_names: List of field names for the model
        framework: The framework to use ('angular' or 'django')
        
        """
        
        # Create the dynamic part of the script (first few lines)
        dynamic_part = f"""#!/bin/bash

APP_NAME="{app_name}"      # Used in API URL
MODEL_NAME="{model_name}"    # Model name
FIELDS="{' '.join(field_names)}"  # Fields for the model
"""

        # Load the static part from a template file
        static_part = self._get_static_script_template(framework)
        
        # Combine the parts
        script_content = dynamic_part + "\n" + static_part
        
        return script_content
    
    def _get_static_script_template(self, framework):
        """Read the static part of the script from a template file based on framework
    
        Args:
            framework: The framework to use ('angular' or 'django')
        """
        if framework.lower() not in ["angular", "django"]:
            framework = "angular"  # Default to angular if invalid framework specified
            
        template_file = f"{framework.lower()}_init.sh"
        template_path = os.path.join(settings.BASE_DIR, 'scripts', template_file)
        
        try:
            with open(template_path, 'r') as file:
                
                
                return file.read()
        except FileNotFoundError:
            # If template file doesn't exist, return empty string or raise an error
                return ""

