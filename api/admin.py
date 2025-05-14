from django.contrib import admin
from .models import Framework, Project , User
from django.contrib.auth.admin import UserAdmin

class ProjectAdmin(admin.ModelAdmin):
    # Update list_display to use tables instead of model_name
    list_display = ('project_name', 'tables', 'framework', 'user', 'date_creation', 'date_modification')
    list_filter = ('framework', 'date_creation')
    # Update search_fields as well
    search_fields = ('project_name',)
    readonly_fields = ('date_creation', 'date_modification')
    # Add a method to display selected tables in admin
  

admin.site.register(Framework)
admin.site.register(Project, ProjectAdmin)




class CustomUserAdmin(UserAdmin):
    # Add user_type to the list display
    list_display = ('username', 'email', 'first_name', 'last_name', 'user_type', 'is_staff')
    
    # Add user_type to the fieldsets
    fieldsets = (
        (None, {'fields': ('username', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'email')}),
        ('User type', {'fields': ('user_type',)}),
        ('Permissions', {
            'fields': ('is_active', 'is_staff', 'is_superuser', 'groups', 'user_permissions'),
        }),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    
    # Add user_type to the add fieldsets
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('username', 'password1', 'password2', 'user_type'),
        }),
    )
    
    # Add a filter for user_type
    list_filter = UserAdmin.list_filter + ('user_type',)
    
    # Allow searching by user_type
    search_fields = UserAdmin.search_fields + ('user_type',)

# Register the custom User model with the custom admin class
admin.site.register(User, CustomUserAdmin)