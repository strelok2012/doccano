from django.contrib import admin

from .models import Label, Document, Project
from .models import DocumentAnnotation, SequenceAnnotation, Seq2seqAnnotation
from .resources import DocumentResource, DocumentAnnotationResource
from import_export.admin import ImportExportModelAdmin, ImportExportMixin


class DocumentAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = DocumentResource
    model = Document
    actions = ['delete_model']

    def get_actions(self, request):
        actions = super().get_actions(request)
        del actions['delete_selected']
        return actions

    def delete_model(self, request, obj):
        for o in obj.all():
            o.delete()
    delete_model.short_description = 'Delete selected Docs'


class DocumentAnnotationAdmin(ImportExportMixin, admin.ModelAdmin):
    resource_class = DocumentAnnotationResource


admin.site.register(DocumentAnnotation, DocumentAnnotationAdmin)
admin.site.register(SequenceAnnotation)
admin.site.register(Seq2seqAnnotation)
admin.site.register(Label)
admin.site.register(Document, DocumentAdmin)
admin.site.register(Project)


from django.contrib.auth.admin import UserAdmin
from django.contrib.auth.models import User

class CustomUserAdmin(UserAdmin):
    def __init__(self, *args, **kwargs):
        super(UserAdmin,self).__init__(*args, **kwargs)
        # UserAdmin.list_display = list(UserAdmin.list_display) + ['date_joined', 'last_login']
        UserAdmin.list_display = ['username', 'email', 'is_active', 'is_staff', 'date_joined', 'last_login', 'num_annotations']

    # Function to count objects of each user from another Model (where user is FK)
    def num_annotations(self, obj):
         return obj.documentannotation_set.count()

admin.site.unregister(User)
admin.site.register(User, CustomUserAdmin)
