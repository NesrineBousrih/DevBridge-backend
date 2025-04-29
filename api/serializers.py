
from rest_framework import serializers
from .models import  Framework, Project
from django.contrib.auth.models import User

        
class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'password')
        read_only_fields = ('id',)

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            password=validated_data['password']
        )
        return user

    def update(self, instance, validated_data):
        # Update username if provided
        if 'username' in validated_data:
            instance.username = validated_data['username']
        
        # Update password if provided
        if 'password' in validated_data:
            instance.set_password(validated_data['password'])
        
        instance.save()
        return instance
    
class FrameworkSerializer(serializers.ModelSerializer):
    class Meta:
        model = Framework
        fields = ['id', 'name', 'logo', 'short_description', 'date_creation', 'date_modification','type']    
        
class ProjectSerializer(serializers.ModelSerializer):
    framework_name = serializers.ReadOnlyField(source='framework.name')
    username = serializers.ReadOnlyField(source='user.username')
    script_url = serializers.SerializerMethodField()
    zip_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = ['id', 'project_name', 'tables', 'framework', 
                  'framework_name', 'user', 'username',
                  'date_creation', 'date_modification', 'script_file', 'script_url', 'zip_file', 'zip_url']
        read_only_fields = ['date_creation', 'date_modification', 'script_url', 'zip_url']
    
    def get_script_url(self, obj):
        if obj.script_file:
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.script_file.url)
        return None
        
    def get_zip_url(self, obj):
        if obj.zip_file:
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.zip_file.url)
        return None


class ProjectCreateSerializer(serializers.ModelSerializer):
    script_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = ['id', 'project_name', 'tables', 'framework', 'user', 'script_file', 'script_url']
        read_only_fields = ['script_url']
    
    def create(self, validated_data):
        # Simply create the project with the tables JSON field
        project = Project.objects.create(**validated_data)
        return project
        
    def get_script_url(self, obj):
        if obj.script_file:
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.script_file.url)
        return None
    
    def validate_tables(self, value):
        """
        Validate the structure of the tables JSON data.
        Each table should have a name and fields.
        """
        for table in value:
            if not isinstance(table, dict):
                raise serializers.ValidationError("Each table must be an object")
            
            if 'table_name' not in table:
                raise serializers.ValidationError("Each table must have a 'table_name'")
                
            if 'fields' not in table or not isinstance(table['fields'], list):
                raise serializers.ValidationError("Each table must have a 'fields' list")
                
            for field in table['fields']:
                if not isinstance(field, dict):
                    raise serializers.ValidationError("Each field must be an object")
                
                # Check for required field properties
                if 'name' not in field:
                    raise serializers.ValidationError("Each field must have a 'name'")
                if 'type' not in field:
                    raise serializers.ValidationError("Each field must have a 'type'")
                
        return value