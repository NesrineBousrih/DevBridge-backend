
from rest_framework import serializers
from .models import  Framework, Project,Field
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
        

class FieldSerializer(serializers.ModelSerializer):
    class Meta:
        model = Field
        fields = ['id', 'name', 'field_type', 'project']
        read_only_fields = ['project']

class ProjectSerializer(serializers.ModelSerializer):
    fields = FieldSerializer(many=True, read_only=True)
    framework_name = serializers.ReadOnlyField(source='framework.name')
    username = serializers.ReadOnlyField(source='user.username')
    script_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = ['id', 'project_name', 'model_name', 'framework', 
                  'framework_name', 'user', 'username', 'fields', 
                  'date_creation', 'date_modification','script_file','script_url']
        read_only_fields = ['date_creation', 'date_modification','script_file']
    def get_script_url(self, obj):
        if obj.script_file:
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.script_file.url)
        return None    
    

class ProjectCreateSerializer(serializers.ModelSerializer):
    fields = FieldSerializer(many=True, required=False)
    script_url = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = ['id', 'project_name', 'model_name', 
                  'framework', 'user', 'fields','script_url']
        read_only_fields=['script_url',]
    
    
    def create(self, validated_data):
        fields_data = validated_data.pop('fields', [])
        project = Project.objects.create(**validated_data)
        
        for field_data in fields_data:
            Field.objects.create(project=project, **field_data)
        
        return project
    def get_script_url(self, obj):
        if obj.script_file:
            request = self.context.get('request')
            if request is not None:
                return request.build_absolute_uri(obj.script_file.url)
        return None 
    
    