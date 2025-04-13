from django.contrib import admin
from .models import Framework, Project,Field
class FieldInline(admin.StackedInline):
    model = Field
    extra = 1
    fields = ('name', 'field_type')

class ProjectAdmin(admin.ModelAdmin):
    list_display = ('project_name', 'model_name', 'framework', 'user', 'date_creation', 'date_modification')
    list_filter = ('framework', 'date_creation')
    search_fields = ('project_name', 'model_name')
    readonly_fields = ('date_creation', 'date_modification')
    inlines = [FieldInline]

admin.site.register(Framework)
admin.site.register(Project,ProjectAdmin)
