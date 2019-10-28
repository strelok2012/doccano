import csv
import json
from io import TextIOWrapper, StringIO, BytesIO
import itertools as it
import logging
import datetime
import pandas as pd

import s3fs
import requests

from string import Template

from django.contrib.auth.views import LoginView as BaseLoginView
from django.urls import reverse
from django.http import HttpResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.views import View
from django.views.generic import TemplateView, CreateView
from django.views.generic.list import ListView
from django.contrib.auth.mixins import LoginRequiredMixin
from django.contrib import messages
from django.db import connection

import os
from django.contrib.auth.models import User

from django.contrib.auth.forms import UserCreationForm

from .resources import DocumentResource, DocumentAnnotationResource, LabelResource, DocumentMLMAnnotationResource, UserResource, ProjectResource

from .permissions import SuperUserMixin
from .forms import ProjectForm
from .models import Document, Project, DocumentAnnotation, DocumentMLMAnnotation, Label, DocumentGoldAnnotation, User
from app import settings
from django.core.exceptions import ObjectDoesNotExist

from server.api import get_labels_admin
from app.settings import ML_FOLDER, BASE_DIR

logger = logging.getLogger(__name__)


def download_file(data, spl, redirect):
    def get_csv(self, filename, data):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}.csv"'.format(filename)
        response.write(data.to_csv())
        return response

    filename = '_'.join(spl)
    try:
        return self.get_csv(filename, data)
    except Exception as e:
        logger.exception(e)
        messages.add_message(request, messages.ERROR, "Something went wrong")
        return HttpResponseRedirect(redirect)




class IndexView(TemplateView):
    template_name = 'index.html'


class ProjectView(LoginRequiredMixin, TemplateView):
    def get_template_names(self):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        if not self.request.user.is_superuser:
            try:
                user = project.users.get(id=self.request.user.id)
            except ObjectDoesNotExist:
                return '404.html'
        return [project.get_template_name()]

    def get_context_data(self, **kwargs):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        context = super().get_context_data(**kwargs)
        context['docs_count'] = project.get_docs_count()
        context['project_name'] = project.get_project_name()
        context['project'] = project
        return context


class ProjectsView(LoginRequiredMixin, CreateView):
    form_class = ProjectForm
    template_name = 'projects.html'

    def form_valid(self, form):
        duplicate_project = self.request.POST.get('duplicate_project')
        if (duplicate_project and len(duplicate_project)):
            to_duplicate = Project.objects.get(pk=duplicate_project)
            if (to_duplicate):
                self.object = to_duplicate.duplicate_object(self.request.POST.get('name'))
        else:
            self.object = form.save()
        return HttpResponseRedirect(self.get_success_url())
    def form_invalid(self, form):
        duplicate_project = self.request.POST.get('duplicate_project')
        if (duplicate_project and len(duplicate_project)):
            to_duplicate = Project.objects.get(pk=duplicate_project)
            if (to_duplicate):
                self.object = to_duplicate.duplicate_object(self.request.POST.get('name'), self.request.POST.get('duplicate_labels'))
                return HttpResponseRedirect(self.get_success_url())

    def get_context_data(self, **kwargs):
        projects = Project.objects.all()
        context = super().get_context_data(**kwargs)
        context['projects'] = projects
        return context

class UsersAdminView(SuperUserMixin, LoginRequiredMixin, CreateView):
    form_class = UserCreationForm
    template_name = 'users.html'

    def form_invalid(self, form):
        response = super().form_invalid(form)
        return response



class DatasetView(SuperUserMixin, LoginRequiredMixin, ListView):
    template_name = 'admin/dataset.html'
    paginate_by = 5

    def get_queryset(self):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        return project.documents.all()

    def get_context_data(self, **kwargs):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        context = super().get_context_data(**kwargs)
        context['docs_count'] = project.get_docs_count()
        return context


class LabelView(SuperUserMixin, LoginRequiredMixin, TemplateView):
    template_name = 'admin/label.html'

    def get_context_data(self, **kwargs):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        context = super().get_context_data(**kwargs)
        context['docs_count'] = project.get_docs_count()
        return context


class UserView(SuperUserMixin, LoginRequiredMixin, TemplateView):
    template_name = 'user.html'

    def get_context_data(self, **kwargs):
        user = get_object_or_404(User, pk=self.kwargs['user_id'])
        context = super().get_context_data(**kwargs)
        return context

class LabelersView(SuperUserMixin, LoginRequiredMixin, TemplateView):
    template_name = 'admin/labelers.html'

    def get_context_data(self, **kwargs):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        context = super().get_context_data(**kwargs)
        context['docs_count'] = project.get_docs_count()
        return context


class LabelAdminView(SuperUserMixin, LoginRequiredMixin, TemplateView):
    template_name = 'admin/labels_admin.html'

    def get_context_data(self, **kwargs):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        context = super().get_context_data(**kwargs)
        context['docs_count'] = project.get_docs_count()
        return context

class UserInfoView(SuperUserMixin, LoginRequiredMixin, TemplateView):
    template_name = 'admin/user_info.html'

    def get_context_data(self, **kwargs):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        context = super().get_context_data(**kwargs)
        context['docs_count'] = project.get_docs_count()
        cursor = connection.cursor()
        annots_sql = '''SELECT server_documentannotation.document_id,
            server_documentannotation.label_id,
            server_documentannotation.user_id,
            server_documentannotation.created_date_time,
            server_documentannotation.updated_date_time
            FROM server_documentannotation
            LEFT JOIN server_document ON server_document.id = server_documentannotation.document_id
            WHERE server_document.project_id = {project_id}
            AND server_documentannotation.user_id = {user_id}'''.format(project_id=self.kwargs['project_id'], user_id=self.kwargs['user_id'])
        cursor.execute(annots_sql)

        annots_csv = 'user_id,created_date_time,updated_date_time\n'
        for row in cursor.fetchall():
            annots_csv += '%s,%s,%s\n' % (row[2], row[3], row[4])
        pandas_csv = StringIO(annots_csv)
        df = pd.read_csv(pandas_csv, parse_dates=['created_date_time', 'updated_date_time'])
        df = df.sort_values(['user_id', 'created_date_time'])
        users_sessions = pd.DataFrame()
        users_speed = {}
        TH_TIMEOUT_SESSION = 15
        for user_id in df['user_id'].unique():
            d = df[df['user_id'] == user_id]
            d['session'] = d['created_date_time'] - d['created_date_time'].shift()
            d['session'] = (d['session'] > datetime.timedelta(minutes=TH_TIMEOUT_SESSION)).cumsum()
            single_user_sessions = d.groupby('session')['created_date_time'].agg([('count', lambda x: len(x) - 1),
                                                                    ('start_datetime', lambda x: x.iloc[0]),
                                                                    ('end_datetime', lambda x: x.iloc[-1]),
                                                                    ('timediff', lambda x: x.iloc[-1] - x.iloc[0])
                                                        ])
            single_user_sessions['user_id'] = user_id
            users_speed[user_id] = sum(single_user_sessions['timediff'].dt.seconds) / sum(single_user_sessions['count'].astype(int))
            users_sessions = pd.concat([users_sessions, single_user_sessions])
        context['user_speed'] = users_speed[self.kwargs['user_id']]

        user_query = ''' 
        WITH da as (
            SELECT MAX(server_documentannotation.updated_date_time) as last_annotation 
            FROM server_documentannotation 
            WHERE server_documentannotation.user_id = %s
        ),
        ut as(SELECT email, id, username FROM auth_user WHERE auth_user.id = %s),
        pt as(
            SELECT server_project.name as project_name, server_project.id as project_id
            FROM server_project
            INNER JOIN server_project_users
            ON server_project_users.project_id = server_project.id
            WHERE server_project_users.user_id = %s
        )

        SELECT ut.id, ut.email, ut.username, da.last_annotation,  pt.project_id, pt.project_name 
        FROM da, ut, pt
        '''  % (self.kwargs['user_id'], self.kwargs['user_id'], self.kwargs['user_id'])

        cursor.execute(user_query)
        rows = cursor.fetchall()
        context['user_id'] = rows[0][0]
        context['user_email'] = rows[0][1]
        context['user_name'] = rows[0][2]
        context['last_annotation'] = rows[0][3]

        projects = []
        for row in rows:
            projects.append({'id': row[4],'name': row[5]})
        context['projects'] = projects
        return context

class StatsView(SuperUserMixin, LoginRequiredMixin, TemplateView):
    template_name = 'admin/stats.html'

    def get_context_data(self, **kwargs):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        context = super().get_context_data(**kwargs)
        context['docs_count'] = project.get_docs_count()
        context['project'] = project
        return context


class MachineLearningModelView(SuperUserMixin, LoginRequiredMixin, TemplateView):
    template_name = 'admin/ml_model.html'


    def get_context_data(self, **kwargs):
        project_id = self.kwargs['project_id']
        # project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        context = super().get_context_data(**kwargs)

        def get_img_data_from_file(filename):
            print(os.path.abspath(filename))
            import base64
            try:
                with open(filename, "rb") as image_file:
                    encoded_string = base64.b64encode(image_file.read()).decode()
            except FileNotFoundError:
                encoded_string = 'missing_graph'

            return encoded_string

        try:
            ml_model_results_filename = os.path.join(ML_FOLDER, 'ml_model_results_{}.txt'.format(project_id))
            print(ml_model_results_filename)
            with open(ml_model_results_filename, 'rt') as f:
                model_results = f.read()


        except Exception as e:
            print(e)
            model_results = 'Could not locate the results of a Machine Learning model. You can try to train a new model.'

        context['model_results'] = model_results
        context['image_precision_recall_curve'] = get_img_data_from_file(
            BASE_DIR+'/staticfiles/images/models/precision_recall_curve_{}.png'.format(project_id))
        context['image_roc_curve'] = get_img_data_from_file(
            BASE_DIR+'/staticfiles/images/models/roc_curve_{}.png'.format(project_id))
        context['image_confidence_accuracy_graph'] = get_img_data_from_file(
            BASE_DIR+'/staticfiles/images/models/confidence_accuracy_graph_{}.png'.format(project_id))
        context['image_learning_curve'] = get_img_data_from_file(
            BASE_DIR+'/staticfiles/images/models/learning_curve_{}.png'.format(project_id))
        return context


class GuidelineView(SuperUserMixin, LoginRequiredMixin, TemplateView):
    template_name = 'admin/guideline.html'

    def get_context_data(self, **kwargs):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        context = super().get_context_data(**kwargs)
        context['docs_count'] = project.get_docs_count()
        return context

class SettingsView(SuperUserMixin, LoginRequiredMixin, TemplateView):
    template_name = 'admin/settings.html'

    def get_context_data(self, **kwargs):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        context = super().get_context_data(**kwargs)
        context['project'] = project
        context['docs_count'] = project.get_docs_count()
        return context


class DataUpload(SuperUserMixin, LoginRequiredMixin, TemplateView):
    template_name = 'admin/dataset_upload.html'

    class ImportFileError(Exception):
        def __init__(self, message):
            self.message = message

    def extract_metadata_csv(self, row, text_col, header_without_text):
        vals_without_text = [val for i, val in enumerate(row) if i != text_col]
        return json.dumps(dict(zip(header_without_text, vals_without_text)))

    def csv_to_documents(self, project, file, text_key='text'):
        form_data = TextIOWrapper(file, encoding='utf-8', errors='ignore')
        reader = csv.reader(form_data)

        maybe_header = next(reader)
        if maybe_header:
            if text_key in maybe_header:
                text_col = maybe_header.index(text_key)
            elif len(maybe_header) == 1:
                reader = it.chain([maybe_header], reader)
                text_col = 0
            else:
                raise DataUpload.ImportFileError("CSV file must have either a title with \"text\" column or have only one column ")

            header_without_text = [title for i, title in enumerate(maybe_header)
                                   if i != text_col]
            fixed_utf = []

            return (
                Document(
                    text=row[text_col],
                    metadata=self.extract_metadata_csv(row, text_col, header_without_text),
                    project=project
                )
                for row in reader
                if row!=[] and row!=''
            )
        else:
            return []

    def labeled_csv_to_labels(self, project, file, text_key='text', label_key='label'):
        form_data = TextIOWrapper(file, encoding='utf-8', errors='ignore')
        reader = csv.reader(form_data, quotechar='"', delimiter=',',
                     quoting=csv.QUOTE_ALL, skipinitialspace=True)

        maybe_header = next(reader)
        if maybe_header:
            if (text_key in maybe_header and label_key in maybe_header):
                text_col = maybe_header.index(text_key)
                label_col = maybe_header.index(label_key)
            elif len(maybe_header) == 2:
                reader = it.chain([maybe_header], reader)
                text_col = 0
                label_col = 1
            else:
                raise DataUpload.ImportFileError("CSV file must have either a title with \"text\" column and \"label\" column or have two columns ")
            errors = []
            labels_set = []
            count = 0
            for row in reader:
                if row[text_col]=='':
                    continue
                label_obj = Label.objects.filter(text__exact=row[label_col], project=project)
                if len(label_obj)>1:
                    errors.append('Found multiple labels with text "{}"'.format(row[label_col]))
                    continue
                else:
                    label_obj = label_obj.first()

                document_obj = Document.objects.filter(text__exact=row[text_col], project=project)
                if len(document_obj) > 1:
                    errors.append('Found multiple documents with text "{}"'.format(row[text_col]))
                    continue
                else:
                    document_obj = document_obj.first()

                if (label_obj and document_obj):
                    labels_set.append([label_obj, document_obj])
                else:
                    if (not label_obj):
                        errors.append('Label "' + row[label_col] + '" is not found')
                    if (not document_obj):
                        errors.append('Document with text "' + row[text_col] + '" is not found')
            if len(errors):
                raise DataUpload.ImportFileError('Encoutered {} errors: \n\n{}'.format(len(errors), '\n\n'.join(errors)) )

            return (
                DocumentGoldAnnotation(
                    label=label[0],
                    document=label[1]
                )
                for label in labels_set
            )
        else:
            return []

    def users_labeled_csv_to_labels(self, project, file, text_key='text', label_key='label', user_key='user'):
        form_data = TextIOWrapper(file, encoding='utf-8', errors='ignore')
        reader = csv.reader(form_data, quotechar='"', delimiter=',',
                     quoting=csv.QUOTE_ALL, skipinitialspace=True)

        maybe_header = next(reader)
        if maybe_header:
            if (text_key in maybe_header and label_key in maybe_header and user_key in maybe_header):
                text_col = maybe_header.index(text_key)
                label_col = maybe_header.index(label_key)
                user_col = maybe_header.index(user_key)
            elif len(maybe_header) == 3:
                reader = it.chain([maybe_header], reader)
                text_col = 0
                label_col = 1
                user_col = 2
            else:
                raise DataUpload.ImportFileError("CSV file must either have a first row with the column titles \"text\", \"label\" and \"user\", or have three columns in that order.")
            errors = []
            labels_set = []
            count = 0
            for row in reader:
                if row[text_col]=='':
                    continue
                label_obj = Label.objects.filter(text__exact=row[label_col], project=project)
                if len(label_obj)>1:
                    errors.append('Found multiple labels with text "{}"'.format(row[label_col]))
                    continue
                else:
                    label_obj = label_obj.first()

                document_obj = Document.objects.filter(text__exact=row[text_col], project=project)
                if len(document_obj) > 1:
                    errors.append('Found multiple documents with text "{}"'.format(row[text_col]))
                    continue
                else:
                    document_obj = document_obj.first()

                user_obj = User.objects.filter(username__exact=row[user_col])

                if len(user_obj) > 1:
                    errors.append('Found multiple users with name "{}"'.format(row[user_col]))
                    continue
                else:
                    user_obj = user_obj.first()

                if (label_obj and document_obj and user_obj):
                    labels_set.append([label_obj, document_obj, user_obj])
                else:
                    if (not label_obj):
                        errors.append('Label "' + row[label_col] + '" is not found')
                    if (not document_obj):
                        errors.append('Document with text "' + row[text_col] + '" is not found')
                    if (not user_obj):
                        errors.append('User with name "' + row[user_col] + '" is not found')
            if len(errors):
                raise DataUpload.ImportFileError('Encoutered {} errors: \n\n{}'.format(len(errors), '\n\n'.join(errors)) )

            return (
                DocumentAnnotation(
                    label=label[0],
                    document=label[1],
                    user=label[2]
                )
                for label in labels_set
            )
        else:
            return []

    def extract_metadata_json(self, entry, text_key):
        copy = entry.copy()
        del copy[text_key]
        return json.dumps(copy)

    def json_to_documents(self, project, file, text_key='text'):
        parsed_entries = (json.loads(line) for line in file)

        return (
            Document(text=entry[text_key], metadata=self.extract_metadata_json(entry, text_key), project=project)
            for entry in parsed_entries
        )

    def post(self, request, *args, **kwargs):
        project = get_object_or_404(Project, pk=kwargs.get('project_id'))
        import_format = request.POST['format']
        try:
            if (request.POST['url']):
                s3 = s3fs.S3FileSystem(anon=False)
                file = s3.open(request.POST['url'], 'rb')
                import_format = import_format.replace('_url', '')
            else:
                file = request.FILES['file'].file
            documents = []
            true_labels = []
            users_lsbels = []
            if import_format == 'csv':
                documents = self.csv_to_documents(project, file)
            elif import_format == 'json':
                documents = self.json_to_documents(project, file)
            elif import_format == 'csv_labeled':
                true_labels = self.labeled_csv_to_labels(project, file)
            elif import_format == "csv_labeled_users":
                users_lsbels = self.users_labeled_csv_to_labels(project, file)

            batch_size = settings.IMPORT_BATCH_SIZE

            if (import_format == 'csv' or import_format == 'json'):
                docs_len = 0
                while True:
                    batch = list(it.islice(documents, batch_size))
                    if not batch:
                        break
                    docs_len += len(batch)
                    Document.objects.bulk_create(batch, batch_size=batch_size)
                url = reverse('dataset', args=[project.id])
                url += '?docs_count=' + str(docs_len)
                return HttpResponseRedirect(url)
            elif (import_format == 'csv_labeled'):
                labels_len = 0
                while True:
                    batch = list(it.islice(true_labels, batch_size))
                    if not batch:
                        break
                    labels_len += len(batch)
                    DocumentGoldAnnotation.objects.bulk_create(batch, batch_size=batch_size)
                url = reverse('dataset', args=[project.id])
                url += '?true_labels_count=' + str(labels_len)
                return HttpResponseRedirect(url)
            elif (import_format == "csv_labeled_users"):
                labels_len = 0
                while True:
                    batch = list(it.islice(users_lsbels, batch_size))
                    if not batch:
                        break
                    labels_len += len(batch)
                    DocumentAnnotation.objects.bulk_create(batch, batch_size=batch_size)
                url = reverse('dataset', args=[project.id])
                url += '?users_labels_count=' + str(labels_len)
                

        except DataUpload.ImportFileError as e:
            messages.add_message(request, messages.ERROR, e.message)
            return HttpResponseRedirect(reverse('upload', args=[project.id]))
        except Exception as e:
            logger.exception(e)
            messages.add_message(request, messages.ERROR, 'Something went wrong')
            messages.add_message(request, messages.ERROR, e)
            return HttpResponseRedirect(reverse('upload', args=[project.id]))
    
    def get_context_data(self, **kwargs):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        context = super().get_context_data(**kwargs)
        context['docs_count'] = project.get_docs_count()
        return context


class DataDownload(SuperUserMixin, LoginRequiredMixin, TemplateView):
    template_name = 'admin/dataset_download.html'

    def get_context_data(self, **kwargs):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        context = super().get_context_data(**kwargs)
        context['docs_count'] = project.get_docs_count()
        return context


class DocumentExport(SuperUserMixin, LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        queryset = Document.objects.filter(project=project)
        dataset = DocumentResource().export(queryset)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}_documents.csv"'.format(project)
        response.write(dataset.csv)
        return response

class DataExportToS3(SuperUserMixin, LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        s3 = s3fs.S3FileSystem(anon=False)

        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        project_type = Project.project_types[project.project_type]['type']

        if project_type=='DocumentClassification':
            query = """
                    SELECT
                server_document.id AS document_id,
                server_documentannotation.id AS annotation_id,
                server_documentannotation.created_date_time AS annotation_datetime,
                server_documentannotation.user_id,
                auth_user.username AS username,
                server_documentannotation.label_id,
                server_label.text AS label_text,
                server_documentgoldannotation.label_id AS gold_label_id,
                server_documentmlmannotation .label_id AS machine_learning_model_predicted_label_id,
                server_document.text,
                server_document.metadata

            FROM server_documentannotation
                RIGHT JOIN server_document ON server_documentannotation.document_id = server_document.id
                LEFT JOIN server_label ON server_documentannotation.label_id = server_label.id
                LEFT JOIN auth_user ON auth_user.id = server_documentannotation.user_id
                LEFT JOIN server_documentgoldannotation ON server_document.id = server_documentgoldannotation.document_id
                LEFT JOIN server_documentmlmannotation ON server_document.id = server_documentmlmannotation.document_id
            WHERE server_document.project_id = {}
                    """.format(int(project.id))
            columns = ['document_id', 'annotation_id', 'annotation_datetime', 'user_id', 'username', 'label_id', 'label_text', 'gold_label_id', 'machine_learning_model_predicted_label_id', 'document_text', 'document_metadata']

        elif project_type=='SequenceLabeling':
            query = """
                    SELECT
                server_document.id AS document_id,
                server_documentannotation.id AS annotation_id,
                server_documentannotation.created_date_time AS annotation_datetime,
                server_documentannotation.user_id,
                auth_user.username AS username,
                server_documentannotation.label_id,
                server_label.text AS label_text,
                server_documentgoldannotation.label_id AS gold_label_id,
                server_documentannotation.start_offset,
                server_documentannotation.end_offset,
                server_document.text,
                server_document.metadata

            FROM server_sequenceannotation AS server_documentannotation
                RIGHT JOIN server_document ON server_documentannotation.document_id = server_document.id
                LEFT JOIN server_label ON server_documentannotation.label_id = server_label.id
                LEFT JOIN auth_user ON auth_user.id = server_documentannotation.user_id
                LEFT JOIN server_documentgoldannotation ON server_document.id = server_documentgoldannotation.document_id
            WHERE server_document.project_id = {}
                    """.format(int(project.id))
            columns = ['document_id', 'annotation_id', 'annotation_datetime', 'user_id', 'username', 'label_id', 'label_text', 'gold_label_id', 'start_offset', 'end_offset', 'document_text', 'document_metadata']

        elif project_type=='Seq2seq':
            query = """
                    SELECT
                server_document.id AS document_id,
                server_documentannotation.id AS annotation_id,
                server_documentannotation.created_date_time AS annotation_datetime,
                server_documentannotation.user_id,
                auth_user.username AS username,
                server_documentannotation.text AS annotation_text,
                server_document.text,
                server_document.metadata

            FROM server_seq2seqannotation AS server_documentannotation
                RIGHT JOIN server_document ON server_documentannotation.document_id = server_document.id
                LEFT JOIN auth_user ON auth_user.id = server_documentannotation.user_id
            WHERE server_document.project_id = {}
                    """.format(int(project.id))
            columns = ['document_id', 'annotation_id', 'annotation_datetime', 'user_id', 'username', 'annotation_text', 'document_text', 'document_metadata']

        else:
            raise Exception('Unidentified project type')

        cursor = connection.cursor()
        cursor.execute(query)

        df = pd.DataFrame(cursor.fetchall(), columns=columns)
        filename = 'gong-datasets/doccano/doccano_project_{}_{}_export.csv'.format(project.id, project.name.replace(' ','_').lower())
        s3_parquet_filename = 's3://'+filename.replace('.csv', '.parquet')
        with s3.open(filename, 'w') as f:
            df.to_csv(f, index=False)
        df.to_parquet(s3_parquet_filename, index=False, allow_truncated_timestamps=True)

        response = HttpResponseRedirect('/projects/{}/stats'.format(project.id))
        return response

class DocumentAnnotationExport(SuperUserMixin, LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        project_docs = Document.objects.filter(project=project)
        queryset = DocumentAnnotation.objects.filter(document__in=project_docs)
        dataset = DocumentAnnotationResource().export(queryset)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}_annotations.csv"'.format(project)
        response.write(dataset.csv)
        return response

class ProjectExport(SuperUserMixin, LoginRequiredMixin, View):

    def get(self, request, *args, **kwargs):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        project_docs = Document.objects.filter(project=project)
        queryset = DocumentAnnotation.objects.filter(document__in=project_docs)
        annotations = DocumentAnnotationResource().export(queryset)

        queryset = DocumentMLMAnnotation.objects.filter(document__in=project_docs)
        mlm_annotations = DocumentMLMAnnotationResource().export(queryset)

        queryset = Label.objects.filter(project=project)
        labels = LabelResource().export(queryset)

        queryset = Document.objects.filter(project=project)
        documents = DocumentResource().export(queryset)

        queryset = User.objects.all()
        users = UserResource().export(queryset)

        queryset = Project.objects.filter(id=self.kwargs['project_id'])
        proj_export = ProjectResource().export(queryset)

        response = HttpResponse(content_type='text/json')
        response['Content-Disposition'] = 'attachment; filename="{}_full_project.json"'.format(project)
        t = Template('''{
            "annotations": ${annotations},
            "mlm_annotations": ${mlm_annotations}
            "labels": ${labels},
            "documents": ${documents},
            "users": ${users},
            "project": ${project}
        }''')
        response.write(t.safe_substitute(annotations=annotations.json, mlm_annotations=mlm_annotations.json, labels=labels.json, documents=documents.json, users=users.json, project=proj_export.json))
        return response


class LabelExport(SuperUserMixin, LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        queryset = Label.objects.filter(project=project)
        dataset = LabelResource().export(queryset)
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}_labels.csv"'.format(project)
        response.write(dataset.csv)
        return response

class DataDownloadFile(SuperUserMixin, LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        project_id = self.kwargs['project_id']
        project = get_object_or_404(Project, pk=project_id)
        docs = project.get_documents(is_null=False).distinct()
        export_format = request.GET.get('format')
        filename = '_'.join(project.name.lower().split())
        try:
            if export_format == 'csv':
                response = self.get_csv(filename, docs)
            elif export_format == 'json':
                response = self.get_json(filename, docs)
            return response
        except Exception as e:
            logger.exception(e)
            messages.add_message(request, messages.ERROR, "Something went wrong")
            return HttpResponseRedirect(reverse('download', args=[project.id]))

    def get_csv(self, filename, docs):
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = 'attachment; filename="{}.csv"'.format(filename)
        writer = csv.writer(response)
        for d in docs:
            writer.writerows(d.to_csv())
        return response

    def get_json(self, filename, docs):
        response = HttpResponse(content_type='text/json')
        response['Content-Disposition'] = 'attachment; filename="{}.json"'.format(filename)
        for d in docs:
            dump = json.dumps(d.to_json(), ensure_ascii=False)
            response.write(dump + '\n')  # write each json object end with a newline
        return response

class LabelsAdminDownloadFile(SuperUserMixin, LoginRequiredMixin, View):
    def get(self, request, *args, **kwargs):
        project = get_object_or_404(Project, pk=self.kwargs['project_id'])
        data = get_labels_admin(project_id=project.id).reset_index()
        spl = project.name.lower().split() + ['labels']

        filename = '_'.join(spl)
        try:
            response = HttpResponse(content_type='text/csv')
            response['Content-Disposition'] = 'attachment; filename="{}.csv"'.format(filename)
            response.write(data.to_csv())
            return response
        except Exception as e:
            logger.exception(e)
            messages.add_message(request, messages.ERROR, "Something went wrong")
            redirect = reverse('labels_admin', args=[project.id])
            return HttpResponseRedirect(redirect)



class LoginView(BaseLoginView):
    template_name = 'login.html'
    redirect_authenticated_user = True
    extra_context = {
        'github_login': bool(settings.SOCIAL_AUTH_GITHUB_KEY),
        'aad_login': bool(settings.SOCIAL_AUTH_AZUREAD_TENANT_OAUTH2_TENANT_ID),
    }

    def get_context_data(self, **kwargs):
        context = super(LoginView, self).get_context_data(**kwargs)
        context['social_login_enabled'] = any(value for key, value in context.items()
                                              if key.endswith('_login'))
        return context


class DemoTextClassification(TemplateView):
    template_name = 'demo/demo_text_classification.html'


class DemoNamedEntityRecognition(TemplateView):
    template_name = 'demo/demo_named_entity.html'


class DemoTranslation(TemplateView):
    template_name = 'demo/demo_translation.html'
