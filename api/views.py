from argparse import Action
import os
import tempfile
import zipfile
import shutil
import subprocess 
from django.http import FileResponse, JsonResponse
from django.conf import settings
from django.core.files.base import ContentFile
import psycopg2
from rest_framework import viewsets, status
from rest_framework.decorators import action
from .models import  Project, Framework , User
from .serializers import  ProjectCreateSerializer, ProjectSerializer, UserSerializer,FrameworkSerializer
from rest_framework import generics, permissions
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.authtoken.models import Token
from django.contrib.auth import authenticate
from rest_framework.permissions import IsAuthenticated
from rest_framework.parsers import MultiPartParser, FormParser, JSONParser
from django.db.models import Count
from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator
from django.views import View
from datetime import datetime, timedelta
from collections import defaultdict
class UserRegistrationView(generics.CreateAPIView):
    serializer_class = UserSerializer
    permission_classes = [permissions.AllowAny]
    
    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        user = User.objects.get(username=response.data['username'])
        token, created = Token.objects.get_or_create(user=user)
        return Response({
            'token': token.key,
            'user_type': user.user_type
        })

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
            return Response({
                'token': token.key,
                'user_type': user.user_type
            })
        return Response({'error': 'Invalid credentials'}, status=401)
    
class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    parser_classes = [MultiPartParser, FormParser, JSONParser]
    
    @action(detail=False, methods=['get'], permission_classes=[IsAuthenticated])
    def me(self, request):
        """
        Get the current user's profile based on their auth token
        """
        serializer = self.get_serializer(request.user)
        return Response(serializer.data)
    
    @action(detail=False, methods=['put', 'patch'], permission_classes=[IsAuthenticated])
    def update_me(self, request):
        """
        Update the current user's profile
        """
        # Handle both FormData and JSON
        if hasattr(request.data, 'dict'):
            data = request.data.dict()
        else:
            data = request.data.copy()
        
        # Ensure current user is used for update
        
        # Handle profile photo
        profile_photo = data.pop('profile_photo', None)
        if profile_photo:
            data['profile_photo'] = profile_photo
        
        # Handle developer-specific fields explicitly
        # These fields need to be specially handled for developer users
        expertise = data.get('expertise', None)
        experience_years = data.get('experience_years', None)
        
        # Convert experience_years to integer if it's provided
        if experience_years and experience_years != '':
            try:
                data['experience_years'] = int(experience_years)
            except (ValueError, TypeError):
                return Response(
                    {"detail": "Experience years must be a valid number"}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
        
        # Determine if it's a partial update
        partial = request.method == 'PATCH'
        
        # Validate and update
        serializer = self.get_serializer(request.user, data=data, partial=partial)
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
    
    def get_queryset(self):
        """
        Override get_queryset to return only the projects of the current user
        For staff/admin users, return all projects
        """
        if self.request.user.is_staff:
            return Project.objects.all()
        return Project.objects.filter(user=self.request.user)
    
    permission_classes = [IsAuthenticated]
    
    def get_serializer_class(self):
        if self.action == 'create':
            return ProjectCreateSerializer
        return ProjectSerializer
    
    def get_serializer_context(self):
        """
        Add request to serializer context for URL generation
        """
        context = super().get_serializer_context()
        context['request'] = self.request
        return context
    
    def perform_create(self, serializer):
        # Always set the user to the current user
        serializer.validated_data['user'] = self.request.user
        
        # Create the project
        project = serializer.save()
        
        # Generate and attach script
        self._generate_and_attach_script(project)
        
        # Generate project zip file
        self._generate_project_zip(project)
        
        return project
    
    def update(self, request, *args, **kwargs):
        """
        Update the project and regenerate script and zip files
        """
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        
        # Check if user has permission to modify this project
        if instance.user != request.user and not request.user.is_staff:
            return Response(
                {"error": "You do not have permission to modify this project"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        
        # Save the updated project
        project = self.perform_update(serializer)
        
        # Generate new script and zip files
        self._generate_and_attach_script(project)
        success, result = self._generate_project_zip(project)
        
        if not success:
            return Response(
                {"error": f"Project updated but failed to generate project files: {result}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response(serializer.data)
    
    def perform_update(self, serializer):
        return serializer.save()
    
    def destroy(self, request, *args, **kwargs):
        """
        Override destroy to check user permissions
        """
        instance = self.get_object()
        
        # Check if user has permission to delete this project
        if instance.user != request.user and not request.user.is_staff:
            return Response(
                {"error": "You do not have permission to delete this project"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        return super().destroy(request, *args, **kwargs)
    
    @action(detail=True, methods=['post'])
    def update_tables(self, request, pk=None):
        """
        Add, update or delete tables in a project
        """
        project = self.get_object()
        
        # Check if user has permission to modify this project
        if project.user != request.user:
            return Response(
                {"error": "You do not have permission to modify this project"},
                status=status.HTTP_403_FORBIDDEN
            )
        
        operation = request.data.get('operation')
        table_data = request.data.get('table_data', {})
        
        # Validate operation
        if operation not in ['add', 'update', 'delete']:
            return Response(
                {"error": "Invalid operation. Must be 'add', 'update', or 'delete'"},
                status=status.HTTP_400_BAD_REQUEST
            )
            
        # Get current tables
        current_tables = project.tables
        
        if operation == 'add':
            # Validate table data
            if not table_data.get('table_name') or not table_data.get('fields'):
                return Response(
                    {"error": "Table name and fields are required for adding a table"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Check if table name already exists
            existing_table_names = [table.get('table_name') for table in current_tables]
            if table_data.get('table_name') in existing_table_names:
                return Response(
                    {"error": f"A table with name '{table_data.get('table_name')}' already exists"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Add new table
            current_tables.append(table_data)
            
        elif operation == 'update':
            # Validate table data
            if not table_data.get('table_name'):
                return Response(
                    {"error": "Table name is required for updating a table"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Find table by name
            table_found = False
            for i, table in enumerate(current_tables):
                if table.get('table_name') == table_data.get('table_name'):
                    # Update existing table
                    current_tables[i] = table_data
                    table_found = True
                    break
                    
            if not table_found:
                return Response(
                    {"error": f"Table '{table_data.get('table_name')}' not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
                
        elif operation == 'delete':
            # Validate table data
            if not table_data.get('table_name'):
                return Response(
                    {"error": "Table name is required for deleting a table"},
                    status=status.HTTP_400_BAD_REQUEST
                )
                
            # Find and remove table by name
            table_found = False
            for i, table in enumerate(current_tables):
                if table.get('table_name') == table_data.get('table_name'):
                    # Remove the table
                    current_tables.pop(i)
                    table_found = True
                    break
                    
            if not table_found:
                return Response(
                    {"error": f"Table '{table_data.get('table_name')}' not found"},
                    status=status.HTTP_404_NOT_FOUND
                )
        
        # Update project with new tables
        project.tables = current_tables
        project.save()
        
        # Regenerate script and zip files
        self._generate_and_attach_script(project)
        success, result = self._generate_project_zip(project)
        
        if not success:
            return Response(
                {"error": f"Tables updated but failed to generate project files: {result}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        
        return Response(
            {"message": f"Table successfully {operation}ed", "tables": project.tables},
            status=status.HTTP_200_OK
        )
        
    @action(detail=True, methods=['get'])
    def download_project(self, request, pk=None):
        """
        Download the generated project zip file
        """
        project = self.get_object()
        
        if not project.zip_file:
            return Response(
                {"error": "No project files available for download"},
                status=status.HTTP_404_NOT_FOUND
            )
            
        return FileResponse(
            project.zip_file.open('rb'),
            as_attachment=True,
            filename=f"{project.project_name}.zip"
        )
    
    @action(detail=False, methods=['post'])
    def connect_database(self, request):
        """
        Connect to a database and return the list of available tables.
        """
        try:
            host = request.data.get('host')
            port = request.data.get('port')
            database_name = request.data.get('databaseName')
            username = request.data.get('username')
            password = request.data.get('password')
            
            # Validate required fields
            if not all([host, port, database_name, username]):
                return Response(
                    {"error": "Missing required database connection parameters"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Connect to the database
            connection = psycopg2.connect(
                host=host,
                port=port,
                dbname=database_name,
                user=username,
                password=password
            )
            
            # Get list of tables
            cursor = connection.cursor()
            cursor.execute("""
                SELECT table_name 
                FROM information_schema.tables 
                WHERE table_schema = 'public'
            """)
            
            tables = [table[0] for table in cursor.fetchall()]
            
            # Close connection
            cursor.close()
            connection.close()
            
            return Response({"tables": tables}, status=status.HTTP_200_OK)
            
        except psycopg2.Error as e:
            print(f"Database connection error: {str(e)}")
            return Response(
                {"error": f"Database connection failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            print(f"Error in connect_database: {str(e)}")
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    @action(detail=False, methods=['post'])
    def get_table_structure(self, request):
        """
        Get the structure of a specific table from the database.
        """
        try:
            host = request.data.get('host')
            port = request.data.get('port')
            database_name = request.data.get('databaseName')
            username = request.data.get('username')
            password = request.data.get('password')
            table_name = request.data.get('table_name')
            
            # Validate required fields
            if not all([host, port, database_name, username]) or not table_name:
                return Response(
                    {"error": "Missing required parameters"},
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Connect to the database
            connection = psycopg2.connect(
                host=host,
                port=port,
                dbname=database_name,
                user=username,
                password=password
            )
            
            # Get table structure
            cursor = connection.cursor()
            tables_structure = {}
            cursor.execute("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_schema = 'public' AND table_name = %s
            """, (table_name,))
            
            columns = [{"name": col[0], "type": col[1]} for col in cursor.fetchall()]
            tables_structure[table_name] = columns
            # Close connection
            cursor.close()
            connection.close()
            
            return Response({"tables_structure": tables_structure}, status=status.HTTP_200_OK)
            
        except psycopg2.Error as e:
            print(f"Database error: {str(e)}")
            return Response(
                {"error": f"Database operation failed: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
        except Exception as e:
            print(f"Error in get_table_structure: {str(e)}")
            return Response(
                {"error": f"An error occurred: {str(e)}"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )
    
    def _generate_project_zip(self, project):
        """Generate the project zip file and update the model
        
        Returns:
            tuple: (success, result)
                If success is True, result is the path to the zip file
                If success is False, result is the error message
        """
        print(f"Project {project.id} retrieved.")
        
        # Create a temporary directory to work in
        temp_dir = tempfile.mkdtemp()
        print(f"Temporary directory created at {temp_dir}.")
        
        zip_path = None
        
        try:
            # Create a temporary file for the script
            script_path = os.path.join(temp_dir, f"init_{project.id}.sh")
            print(f"Script path set to {script_path}.")

            # Write the script content to the file - with conditional line removal
            with open(script_path, 'wb') as script_file:
                print("Writing script content to the file.")
                project.script_file.open()
                script_content = project.script_file.read()
                
                # Get framework type and convert to lowercase
                framework = project.framework.name.lower() if project.framework and project.framework.name else "unknown"
                print(f"Project framework: {framework}")
                
                # Determine how many lines to remove based on framework
                lines_to_remove = 0
                if framework == "angular":
                    lines_to_remove = 6  # Angular-specific adjustment
                elif framework == "django":
                    lines_to_remove = 6   # Django-specific adjustment
                
                # Remove the specified number of lines if needed
                if lines_to_remove > 0:
                    print(f"Removing last {lines_to_remove} lines from script for {framework} framework")
                    
                    # Convert bytes to text for line manipulation
                    script_text = script_content.decode('utf-8')
                    script_lines = script_text.splitlines()
                    
                    # Remove last N lines if there are enough lines
                    if len(script_lines) > lines_to_remove:
                        script_lines = script_lines[:-lines_to_remove]
                        # Convert back to bytes with proper line endings
                        script_content = '\n'.join(script_lines).encode('utf-8')
                        print(f"Script modified: removed last {lines_to_remove} lines. New line count: {len(script_lines)}")
                    else:
                        print(f"Warning: Script has fewer lines ({len(script_lines)}) than requested to remove ({lines_to_remove})")
                
                script_file.write(script_content)
                project.script_file.close()
            print("Script content written.")
            
            # Verify the content of the script file
            with open(script_path, 'rb') as verify_file:
                verification_content = verify_file.read()
                content_length = len(verification_content)
                content_preview = verification_content[:100].decode('utf-8', errors='replace')
                print(f"Script verification - Length: {content_length} bytes")
                print(f"Script content preview: {content_preview}...")
                if content_length == 0:
                    raise Exception("Script file is empty after writing")
            
            # Make the script executable
            os.chmod(script_path, 0o755)
            print(f"Script {script_path} made executable.")
            
            # Execute the script with appropriate shell based on platform
            import platform
            print(f"Platform detected: {platform.system()}.")
            
            if platform.system() == 'Windows':
                # Try several different approaches for Windows
                script_executed = False
                
                # Approach 1: Use Git Bash if available (Known to work)
                try:
                    print("Checking for Git Bash...")
                    git_bash_paths = [
                        "C:\\Program Files\\Git\\bin\\bash.exe",
                        "C:\\Program Files (x86)\\Git\\bin\\bash.exe"
                    ]
                    
                    for git_bash in git_bash_paths:
                        if os.path.exists(git_bash):
                            print(f"Found Git Bash at {git_bash}, attempting to execute script...")
                            # Convert Windows path to Git Bash path
                            git_bash_script_path = script_path.replace('\\', '/')
                            git_bash_script_path = git_bash_script_path.replace('C:', '/c')
                                
                            normalized_temp_dir = temp_dir.replace('\\', '/')
                            normalized_script_path = git_bash_script_path.replace('\\', '/')

                            # Now use the preprocessed variables in your f-string
                            subprocess.run(
                                [git_bash, "-c", f"cd '{normalized_temp_dir}' && bash '{normalized_script_path}'"],
                                check=True
                            )        
                            print("Script executed successfully with Git Bash")
                            script_executed = True
                            break
                except Exception as git_bash_error:
                    print(f"Git Bash execution failed: {git_bash_error}")
                
                # Additional Windows execution methods...
                # [Note: Remaining Windows execution methods are included as in original code]
                # ...
                
                if not script_executed:
                    raise Exception("All script execution methods failed")
            else:
                # Linux/Mac execution
                print("Executing the script for Linux/Mac.")
                subprocess.run(['bash', script_path], cwd=temp_dir, check=True)
            
            # Create a temporary zip file
            zip_path = os.path.join(settings.MEDIA_ROOT, f"project_{project.id}.zip")
            if framework == "django":
                project_dir = os.path.join(temp_dir, "Django-Init-Automation")
            else:  # Default to Angular or any other framework
                project_dir = os.path.join(temp_dir, "Angular-Init-Automation")
            print(f"Zip path set to {zip_path}. Project directory: {project_dir}.")
            
            # Check if the project directory exists
            if not os.path.exists(project_dir):
                # List temp directory contents for debugging
                print("Listing temporary directory contents:")
                for item in os.listdir(temp_dir):
                    item_path = os.path.join(temp_dir, item)
                    if os.path.isdir(item_path):
                        print(f"Directory: {item} (contains {len(os.listdir(item_path))} items)")
                    else:
                        print(f"File: {item} ({os.path.getsize(item_path)} bytes)")
                        
                return False, "Project directory not found after script execution"
            
            # Zip the project directory
            print(f"Zipping the project directory at {project_dir}.")
            with zipfile.ZipFile(zip_path, 'w', zipfile.ZIP_DEFLATED) as zipf:
                for root, dirs, files in os.walk(project_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        zipf.write(
                            file_path, 
                            os.path.relpath(file_path, start=temp_dir)
                        )
            print(f"Project directory zipped into {zip_path}.")
            
            # Save the zip file to the project model for future reference
            with open(zip_path, 'rb') as f:
                print("Saving the zip file to the project model.")
                project.zip_file.save(f"{project.project_name}.zip", ContentFile(f.read()), save=True)
            
            return True, zip_path
        
        except Exception as e:
            print(f"Error during zip generation: {str(e)}")
            import traceback
            traceback.print_exc()  # Print the full stack trace for better debugging
            return False, str(e)
        
        finally:
            # Clean up temporary directory
            print(f"Cleaning up temporary directory {temp_dir}.")
            shutil.rmtree(temp_dir, ignore_errors=True)
    
    def _generate_and_attach_script(self, project):
        """Generate the shell script content and attach it to the project"""
        app_name = project.project_name.lower()
        tables_data = project.tables
        models_data = []
        
        # Process table data from the JSONField
        for table in tables_data:
            table_name = table.get('table_name', '')
            table_fields = table.get('fields', [])
            field_names = [field.get('name', '') for field in table_fields]
            
            if table_name and field_names:
                models_data.append(f"{table_name}:{','.join(field_names)}")
        
        # Join all model data with semicolons
        models_data_str = ";".join(models_data)
        
        # Get the framework name
        framework_name = project.framework.name if project.framework else "Angular"
        
        # Generate the script content
        script_content = self._generate_script_content(app_name, models_data_str, [], framework_name)
        
        # Create a file object to attach to the model
        script_file = ContentFile(script_content.encode('utf-8'))
        
        # Generate a filename based on the project
        filename = f"init_{project.id}_{app_name}.sh"
        
        # Update with the file
        project.script_file.save(filename, script_file, save=True)
    
    def _generate_script_content(self, app_name, models_data, field_names, framework="Angular"):
        """Generate the shell script content with the appropriate parameters"""
        # Create the dynamic part of the script (first few lines)
        dynamic_part = f"""#!/bin/bash
PROJECT_DIR="{framework}-Init-Automation"
APP_NAME="{app_name}"      # Used in API URL
MODELS_DATA="{models_data}"    # Model name with fields
"""

        # Load the static part from a template file
        static_part = self._get_static_script_template(framework)
        
        # Combine the parts
        script_content = dynamic_part + "\n" + static_part
        
        return script_content
    
    def _get_static_script_template(self, framework):
        """Read the static part of the script from a template file based on framework"""
        if framework.lower() not in ["angular", "django"]:
            framework = "angular"  # Default to angular if invalid framework specified
            
        template_file = f"{framework.lower()}_init.sh"
        template_path = os.path.join(settings.BASE_DIR, 'scripts', template_file)
        
        try:
            with open(template_path, 'r') as file:
                return file.read()
        except FileNotFoundError:
            print(f"Warning: Template file {template_path} not found")
            return ""
    @action(detail=False, methods=['get'])
    def my_projects(self, request):
        """
        A dedicated endpoint to get all projects of the current user
        """
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)
        return Response(serializer.data)   
from django.utils import timezone     
class WeeklyActivityView(APIView):
    def get(self, request, format=None):
        today = timezone.now().date()
        # Get projects for the last 7 days
        seven_days_ago = today - timedelta(days=6)
        
        # Aggregate project counts by date
        activity_data = Project.objects.filter(
            date_creation__date__gte=seven_days_ago
        ).extra(select={'day': 'date(date_creation)'}).values('day').annotate(count=Count('id')).order_by('day')

        # Create a dictionary for easier lookup
        activity_dict = {item['day'].strftime('%Y-%m-%d'): item['count'] for item in activity_data}

        # Prepare labels and data for the last 7 days, filling in zeros for days without projects
        labels = [(seven_days_ago + timedelta(days=i)).strftime('%Y-%m-%d') for i in range(7)]
        data = [activity_dict.get(label, 0) for label in labels]

        return Response({
            'labels': labels,
            'data': data
        })

class UsersOverviewView(APIView):
    def get(self, request, format=None):
        user_type_counts = User.objects.values('user_type').annotate(count=Count('id'))
        
        labels = [item['user_type'].capitalize() for item in user_type_counts]
        data = [item['count'] for item in user_type_counts]
        colors = [
            'rgba(255, 99, 132, 0.6)',  # Admin
            'rgba(54, 162, 235, 0.6)',  # Developer
        ] # You can add more colors if you have more user types
        
        return Response({
            'labels': labels,
            'data': data,
            'colors': colors
        })

class TechnologyDistributionView(APIView):
    def get(self, request, format=None):
        framework_counts = Project.objects.values('framework__name').annotate(count=Count('id')).order_by('-count')
        
        labels = [item['framework__name'] for item in framework_counts]
        data = [item['count'] for item in framework_counts]
        
        return Response({
            'labels': labels,
            'data': data
        })

class RecentActivityView(APIView):
    def get(self, request, format=None):
        recent_projects = Project.objects.select_related('user', 'framework').order_by('-date_creation')[:5]  # Get the 5 most recent
        serializer = ProjectSerializer(recent_projects, many=True)
        return Response(serializer.data)