
from rest_framework import serializers
from .models import  Framework, Project, User

class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=False)
    current_password = serializers.CharField(write_only=True, required=False)
    user_type = serializers.ChoiceField(choices=User.USER_TYPE_CHOICES, default='developer')
    email = serializers.EmailField(required=True)
    profile_photo = serializers.ImageField(required=False, allow_null=True)

    class Meta:
        model = User
        fields = ('id', 'username', 'password', 'current_password', 'email', 'user_type', 'profile_photo')
        read_only_fields = ('id',)

    def validate(self, data):
        # If we're creating a new user, password must be provided
        if self.instance is None and not data.get('password'):
            raise serializers.ValidationError({'password': 'This field is required.'})
        
        # Check if new password is provided during update
        if self.instance and data.get('password'):
            # Validate current password when changing password
            current_password = data.get('current_password')
            if not current_password:
                raise serializers.ValidationError({
                    'current_password': 'Current password is required when changing password'
                })
            
            # Check if current password is correct
            if not self.instance.check_password(current_password):
                raise serializers.ValidationError({
                    'current_password': 'Current password is incorrect'
                })
        
        return data

    def create(self, validated_data):
        # Remove non-model fields
        validated_data.pop('current_password', None)
        
        return User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            password=validated_data['password'],
            user_type=validated_data.get('user_type', 'developer')
        )

    def update(self, instance, validated_data):
        # Remove current_password from validated data
        validated_data.pop('current_password', None)
        
        # Handle profile photo
        profile_photo = validated_data.pop('profile_photo', None)
        if profile_photo:
            # Delete existing photo if it exists
            if instance.profile_photo:
                instance.profile_photo.delete()
            
            # Save new photo
            instance.profile_photo = profile_photo

        # Update username, email, and user type
        instance.username = validated_data.get('username', instance.username)
        instance.email = validated_data.get('email', instance.email)
        instance.user_type = validated_data.get('user_type', instance.user_type)

        # Only update the password if it's provided and not empty
        password = validated_data.get('password')
        if password:
            instance.set_password(password)

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