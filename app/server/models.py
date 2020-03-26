import json
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q, Count
from django.urls import reverse
from django.contrib.auth.models import User
from .utils import get_key_choices
from server.project_types import project_types


class Project(models.Model):
    project_types = project_types

    DOCUMENT_CLASSIFICATION = 'DocumentClassification'
    SEQUENCE_LABELING = 'SequenceLabeling'

    SEQUENCE_LABELING_ALT = 'SequenceLabelingAlt'
    Seq2seq = 'Seq2seq'

    PROJECT_CHOICES = ((k, v['title']) for k,v in project_types.items())

    name = models.CharField(max_length=100)
    description = models.CharField(max_length=500)
    guideline = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    users = models.ManyToManyField(User, related_name='projects')
    project_type = models.CharField(max_length=30, choices=PROJECT_CHOICES)
    use_machine_model_sort = models.BooleanField(default=False)
    enable_metadata_search = models.BooleanField(default=False)
    show_ml_model_prediction = models.BooleanField(default=False)
    shuffle_documents = models.BooleanField(default=False)
    sentence_labeling = models.BooleanField(default=True)

    def __init__(self, *args, **kwargs):
        super(Project,self).__init__(*args, **kwargs)
        Project.list_display = ['id', 'name', 'project_type', 'use_machine_model_sort', 'show_ml_model_prediction']

    def get_absolute_url(self):
        return reverse('upload', args=[self.id])

    def is_type_of(self, project_type):
        # return project_type == self.project_type
        return self.project_types[ self.project_type ]['type'] == project_type

    def get_progress(self, user):
        docs = self.get_documents(is_null=True, user=user)
        total = self.documents.count()
        remaining = docs.count()
        return {'total': total, 'remaining': remaining}

    @property
    def image(self):
        url = self.project_types[ self.project_type ]['image']
        return url

    def get_template_name(self):
        template_name = self.project_types[ self.project_type ]['template_html']
        return template_name

    def get_mlm_user(self):
        try:
            mlm_user = User.objects.get(username='MachineLearningModel')
        except User.DoesNotExist:
            mlm_user = None
        return mlm_user

    def get_documents_annotated_by_human_user(self):
        docs = self.documents.all()
        if (self.get_mlm_user()):
            docs = docs.filter(Q(doc_annotations__isnull=False) & ~Q(doc_annotations__user=mlm_user))
        else:
            docs = docs.filter(doc_annotations__isnull=False)
        return docs

    def get_documents_not_annotated_by_human_user(self, user_ids=[]):
        docs = self.documents.all()
        users = User.objects.all().filter(id!=[])
        docs = docs.exclude(doc_annotations__isnull=False) # exclude documents that have annotations
        if (self.get_mlm_user()):
            docs = docs.filter(Q(doc_annotations__isnull=True) | Q(doc_annotations__user=mlm_user))
        else:
            docs = docs.filter(doc_annotations__isnull=False)
        return docs

    def get_documents_kwargs(self, user, labels=None):
        ret = {}
        if not user:
            return ret
        if (labels):
            labels = labels.split(',')
        if self.is_type_of(Project.DOCUMENT_CLASSIFICATION):
            ret["doc_annotations__user"] = user
            if (labels):
                ret[ "doc_annotations__label__in"] = labels
        elif self.is_type_of(Project.SEQUENCE_LABELING_ALT):
            ret["doc_annotations__user"] = user
            if (labels):
                ret[ "doc_annotations__label__in"] = labels
        elif self.is_type_of(Project.SEQUENCE_LABELING):
            ret["seq_annotations__user"] = user
            if (labels):
                ret[ "seq_annotations__label__in"] = labels
        elif self.is_type_of(Project.Seq2seq):
            ret["seq_annotations__user"] = user
            if (labels):
                ret[ "seq_annotations__label__in"] = labels
        else:
            print('Project type: '+self.project_type)
            raise ValueError('Invalid project_type')

        return ret

    def get_unannotated_documents(self, user):
        docs = self.documents
        if not user:
            return docs

        docs = docs.exclude(**self.get_documents_kwargs(user))

        return docs

    def get_annotated_ordering(self):
        if self.shuffle_documents:
            order = '?'
        elif self.use_machine_model_sort:
            order = 'doc_mlm_annotations__prob'
        else:
            order = 'doc_annotations__prob'

        return order
    
    def get_annotated_documents(self, user, labels=None):
        docs = self.documents.filter(project=self.pk)
        if not user:
            return docs
        docs = docs.filter(**self.get_documents_kwargs(user)).order_by(self.get_annotated_ordering())
        return docs.filter(**self.get_documents_kwargs(user, labels)).order_by(self.get_annotated_ordering()).annotate(id_count=Count('id'))
    
    def get_all_documents(self, user):
        docs = self.documents
        if not user:
            return docs
        
        annotated = docs.filter(**self.get_documents_kwargs(user)).order_by(self.get_annotated_ordering()).annotate(id_count=Count('id'))
        unannotated = docs.exclude(**self.get_documents_kwargs(user)).annotate(id_count=Count('id'))

        return unannotated.union(annotated, all=True)

    def get_documents(self, is_null=True, user=None):
        docs = self.documents.all()
        if self.is_type_of(Project.DOCUMENT_CLASSIFICATION):
            if user:
                docs = docs.exclude(doc_annotations__user=user)
            # else:
                # docs = docs.filter(doc_annotations__isnull=is_null)
        elif self.is_type_of(Project.SEQUENCE_LABELING_ALT):
            if user:
                docs = docs.exclude(doc_annotations__user=user)
        elif self.is_type_of(Project.SEQUENCE_LABELING):
            if user:
                docs = docs.exclude(seq_annotations__user=user)
            else:
                docs = docs.filter(seq_annotations__isnull=is_null)
        elif self.is_type_of(Project.Seq2seq):
            if user:
                docs = docs.exclude(seq2seq_annotations__user=user)
            else:
                docs = docs.filter(seq2seq_annotations__isnull=is_null)
        else:
            print('Project type: '+self.project_type)
            raise ValueError('Invalid project_type')

        return docs

    def get_docs_count(self):
        return self.documents.count()

    def get_project_name(self):
        return self.name

    def get_document_serializer(self):
        from .serializers import ClassificationDocumentSerializer
        from .serializers import SequenceDocumentSerializer
        from .serializers import Seq2seqDocumentSerializer
        if self.is_type_of(Project.DOCUMENT_CLASSIFICATION):
            return ClassificationDocumentSerializer
        elif self.is_type_of(Project.SEQUENCE_LABELING_ALT):
            return ClassificationDocumentSerializer
        elif self.is_type_of(Project.SEQUENCE_LABELING):
            return SequenceDocumentSerializer
        elif self.is_type_of(Project.Seq2seq):
            return Seq2seqDocumentSerializer
        else:
            raise ValueError('Invalid project_type')

    def get_annotation_serializer(self):
        from .serializers import DocumentAnnotationSerializer
        from .serializers import SequenceAnnotationSerializer
        from .serializers import Seq2seqAnnotationSerializer
        if self.is_type_of(Project.DOCUMENT_CLASSIFICATION):
            return DocumentAnnotationSerializer
        elif self.is_type_of(Project.SEQUENCE_LABELING_ALT):
            return DocumentAnnotationSerializer
        elif self.is_type_of(Project.SEQUENCE_LABELING):
            return SequenceAnnotationSerializer
        elif self.is_type_of(Project.Seq2seq):
            return Seq2seqAnnotationSerializer

    def get_annotation_class(self):
        if self.is_type_of(Project.DOCUMENT_CLASSIFICATION):
            return DocumentAnnotation
        elif self.is_type_of(Project.SEQUENCE_LABELING_ALT):
            return DocumentAnnotation
        elif self.is_type_of(Project.SEQUENCE_LABELING):
            return SequenceAnnotation
        elif self.is_type_of(Project.Seq2seq):
            return Seq2seqAnnotation

    def __str__(self):
        return self.name

    def duplicate_object(self, new_name, duplicate_labels):
        """
        Duplicate a model instance, making copies of all foreign keys pointing to it.
        There are 3 steps that need to occur in order:

            1.  Enumerate the related child objects and m2m relations, saving in lists/dicts
            2.  Copy the parent object per django docs (doesn't copy relations)
            3a. Copy the child objects, relating to the copied parent object
            3b. Re-create the m2m relations on the copied parent object

        """
        related_objects_to_copy = []
        relations_to_set = {}
        # Iterate through all the fields in the parent object looking for related fields
        for field in self._meta.get_fields():
            if not duplicate_labels and field.name == 'labels':
                continue
            if field.one_to_many:
                # One to many fields are backward relationships where many child 
                # objects are related to the parent. Enumerate them and save a list 
                # so we can copy them after duplicating our parent object.
                # 'field' is a ManyToOneRel which is not iterable, we need to get
                # the object attribute itself.
                print(f'Found a one-to-many field: "{field.name}". Getting records...')
                related_object_manager = getattr(self, field.name)
                related_objects = list(related_object_manager.all())
                if related_objects:
                    print(f' - {len(related_objects)} related objects to copy')
                    related_objects_to_copy += related_objects

            elif field.many_to_one:
                # In testing, these relationships are preserved when the parent
                # object is copied, so they don't need to be copied separately.
                print(f'Found a many-to-one field: "{field.name}"')

            elif field.many_to_many:
                # Many to many fields are relationships where many parent objects
                # can be related to many child objects. Because of this the child
                # objects don't need to be copied when we copy the parent, we just
                # need to re-create the relationship to them on the copied parent.
                # print(f'Found a many-to-many field: {field.name}')
                print(f'Found a many-to-many field: "{field.name}". Getting records...')
                related_object_manager = getattr(self, field.name)
                relations = list(related_object_manager.all())
                if relations:
                    print(f' - {len(relations)} relations to set')
                    relations_to_set[field.name] = relations

        # Duplicate the parent object
        self.pk = None
        self.use_machine_model_sort = False
        if (new_name):
            self.name = new_name
        self.save()
        print('Created a new project. Copying related objects...')
        #print(f'Copied parent object ({str(self)})')

        # Copy the one-to-many child objects and relate them to the copied parent
        data_to_copy = {}
        for related_object in related_objects_to_copy:
            # Iterate through the fields in the related object to find the one that
            # relates to the parent model.
            for related_object_field in related_object._meta.fields:
                if related_object_field.related_model == self.__class__:
                    # If the related_model on this field matches the parent
                    # object's class, perform the copy of the child object and set
                    # this field to the parent object, creating the new
                    # child -> parent relationship.
                    related_object.pk = None
                    setattr(related_object, related_object_field.name, self)
                    # related_object.save()

            data_type = (type(related_object)).__name__
            if data_type not in data_to_copy:
                data_to_copy[data_type] = {
                    'values': [],
                    'type': type(related_object)
                }
            data_to_copy[data_type]['values'].append(related_object)

        for data_type_name, data in data_to_copy.items():
            print('Copying {} records of type {}'.format(len(data['values']), str(data_type)))
            (data['type']).objects.bulk_create( data['values'] )

        print('Copied related fields')

        # Set the many-to-many relations on the copied parent
        for field_name, relations in relations_to_set.items():
            # Get the field by name and set the relations, creating the new
            # relationships.
            field = getattr(self, field_name)
            field.set(relations)
            text_relations = []
            for relation in relations:
                text_relations.append(str(relation))
            #print(f'|- Set {len(relations)} many-to-many relations on {field_name} {text_relations}')

        return self

    # def duplicate_object(self, new_name, duplicate_labels):
    #     from django.db import connection
    #     import datetime
    #     now = str(datetime.datetime.utcnow())
    #     cursor = connection.cursor()
    #
    #     query = """
    #     SELECT
    #     text, metadata
    #     FROM server_document
    #     WHERE project_id = {}""".format(self.id)
    #     cursor.execute(query)
    #     # df = pd.DataFrame(cursor.fetchall(), columns=[
    #     #     'document_id', 'label_id', 'num_labelers', 'last_annotation_date', 'snippet', 'ground_truth', 'model_label',
    #     #     'model_confidence'
    #     # ])
    #     rows = cursor.fetchall()
    #     dataset = [ (row[0], new_project_id, row[1], now, now) for row in rows ]
    #
    #     query = """
    #     INSERT INTO server_document
    #     (text, project_id, metadata, created_date_time, updated_date_time)
    #     VALUES {}
    #     """.format(','.join([str(x) for x in dataset]))
    #     cursor.execute(query)
    #
    #     x = 1
    #     pass


class Label(models.Model):
    KEY_CHOICES = get_key_choices()
    COLOR_CHOICES = ()

    text = models.CharField(max_length=100)
    comment = models.CharField(max_length=2000, default='', blank=True)
    shortcut = models.CharField(max_length=15, blank=True, null=True, choices=KEY_CHOICES)
    project = models.ForeignKey(Project, related_name='labels', on_delete=models.CASCADE)
    background_color = models.CharField(max_length=7, default='#209cee')
    text_color = models.CharField(max_length=7, default='#ffffff')

    def __str__(self):
        return self.text

    class Meta:
        unique_together = (
            ('project', 'text'),
            ('project', 'shortcut')
        )


class Document(models.Model):
    text = models.TextField()
    project = models.ForeignKey(Project, related_name='documents', on_delete=models.CASCADE)
    metadata = models.TextField(default='{}')
    created_date_time = models.DateTimeField(auto_now_add=True)
    updated_date_time = models.DateTimeField(auto_now=True)
    priority = models.IntegerField(null=True)

    def get_annotations(self):
        if self.project.is_type_of(Project.DOCUMENT_CLASSIFICATION):
            return self.doc_annotations.all()
        elif self.project.is_type_of(Project.SEQUENCE_LABELING_ALT):
            return self.doc_annotations.all()
        elif self.project.is_type_of(Project.SEQUENCE_LABELING):
            return self.seq_annotations.all()
        elif self.project.is_type_of(Project.Seq2seq):
            return self.seq2seq_annotations.all()

    def to_csv(self):
        return self.make_dataset()

    def make_dataset(self):
        if self.project.is_type_of(Project.DOCUMENT_CLASSIFICATION):
            return self.make_dataset_for_classification()
        elif self.project.is_type_of(Project.SEQUENCE_LABELING):
            return self.make_dataset_for_sequence_labeling()
        elif self.project.is_type_of(Project.Seq2seq):
            return self.make_dataset_for_seq2seq()

    def make_dataset_for_classification(self):
        annotations = self.get_annotations()
        dataset = [[self.id, self.text, a.label.text, a.user.username, self.metadata]
                   for a in annotations]
        return dataset

    def make_dataset_for_sequence_labeling(self):
        annotations = self.get_annotations()
        dataset = [[self.id, ch, 'O', self.metadata] for ch in self.text]
        for a in annotations:
            for i in range(a.start_offset, a.end_offset):
                if i == a.start_offset:
                    dataset[i][2] = 'B-{}'.format(a.label.text)
                else:
                    dataset[i][2] = 'I-{}'.format(a.label.text)
        return dataset

    def make_dataset_for_seq2seq(self):
        annotations = self.get_annotations()
        dataset = [[self.id, self.text, a.text, a.user.username, self.metadata]
                   for a in annotations]
        return dataset

    def to_json(self):
        return self.make_dataset_json()

    def make_dataset_json(self):
        if self.project.is_type_of(Project.DOCUMENT_CLASSIFICATION):
            return self.make_dataset_for_classification_json()
        elif self.project.is_type_of(Project.SEQUENCE_LABELING):
            return self.make_dataset_for_sequence_labeling_json()
        elif self.project.is_type_of(Project.Seq2seq):
            return self.make_dataset_for_seq2seq_json()

    def make_dataset_for_classification_json(self):
        annotations = self.get_annotations()
        labels = [a.label.text for a in annotations]
        username = annotations[0].user.username
        dataset = {'doc_id': self.id, 'text': self.text, 'labels': labels,
                   'username': username, 'metadata': json.loads(self.metadata)}
        return dataset

    def make_dataset_for_sequence_labeling_json(self):
        annotations = self.get_annotations()
        entities = [(a.start_offset, a.end_offset, a.label.text) for a in annotations]
        username = annotations[0].user.username
        dataset = {'doc_id': self.id, 'text': self.text, 'entities': entities,
                   'username': username, 'metadata': json.loads(self.metadata)}
        return dataset

    def make_dataset_for_seq2seq_json(self):
        annotations = self.get_annotations()
        sentences = [a.text for a in annotations]
        username = annotations[0].user.username
        dataset = {'doc_id': self.id, 'text': self.text, 'sentences': sentences,
                   'username': username, 'metadata': json.loads(self.metadata)}
        return dataset

    def is_labeled_by(self, user):
        annotations = self.get_annotations()
        for a in annotations:
            if (a.user == user):
                return True
        return False

    def __str__(self):
        return self.text[:50]


class Annotation(models.Model):
    prob = models.FloatField(null=True, blank=True, default=None)
    manual = models.BooleanField(default=False)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    created_date_time = models.DateTimeField(auto_now_add=True)
    updated_date_time = models.DateTimeField(auto_now=True)
    additional_data = models.TextField(default='{}')

    class Meta:
        abstract = True

class AnnotationExternal(models.Model):
    prob = models.FloatField(null=True, blank=True, default=None)
    created_date_time = models.DateTimeField(auto_now_add=True)
    updated_date_time = models.DateTimeField(auto_now=True)
    additional_data = models.TextField(default='{}')

    class Meta:
        abstract = True


class DocumentAnnotation(Annotation):
    document = models.ForeignKey(Document, related_name='doc_annotations', on_delete=models.CASCADE)
    label = models.ForeignKey(Label, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('document', 'user', 'label', 'additional_data')

    # def __str__(self):
    #     return 'AAAA'

class DocumentMLMAnnotation(AnnotationExternal):
    document = models.ForeignKey(Document, related_name='doc_mlm_annotations', on_delete=models.CASCADE)
    label = models.ForeignKey(Label, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('document', 'label', 'additional_data')

class DocumentGoldAnnotation(AnnotationExternal):
    document = models.ForeignKey(Document, related_name='doc_gold_annotations', on_delete=models.CASCADE)
    label = models.ForeignKey(Label, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('document', 'label', 'additional_data')


class SequenceAnnotation(Annotation):
    document = models.ForeignKey(Document, related_name='seq_annotations', on_delete=models.CASCADE)
    label = models.ForeignKey(Label, on_delete=models.CASCADE)
    start_offset = models.IntegerField()
    end_offset = models.IntegerField()

    def clean(self):
        if self.start_offset >= self.end_offset:
            raise ValidationError('start_offset is after end_offset')

    class Meta:
        unique_together = ('document', 'user', 'label', 'start_offset', 'end_offset')


class Seq2seqAnnotation(Annotation):
    document = models.ForeignKey(Document, related_name='seq2seq_annotations', on_delete=models.CASCADE)
    text = models.TextField()

    class Meta:
        unique_together = ('document', 'user', 'text')
