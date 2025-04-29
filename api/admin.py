from django.contrib import admin
from .models import Framework, Project


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