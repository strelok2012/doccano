import json
from django.core.exceptions import ValidationError
from django.db import models
from django.db.models import Q
from django.urls import reverse
from django.contrib.auth.models import User
from django.contrib.staticfiles.storage import staticfiles_storage
from .utils import get_key_choices


class Project(models.Model):
    project_types = {
        'DocumentClassification': {
            'title': 'document classification',
            'type': 'DocumentClassification',
            'image': staticfiles_storage.url('images/cat-1045782_640.jpg'),
            'template_html': 'annotation/document_classification.html',
            'document_serializer': '',
            'annotations_serializer': '',
        },

        'SequenceLabeling': {
            'title': 'sequence labeling',
            'type': 'SequenceLabeling',
            'image': staticfiles_storage.url('images/cat-3449999_640.jpg'),
            'template_html': 'annotation/sequence_labeling.html',
            'document_serializer': '',
            'annotations_serializer': '',
        },

        'Seq2seq': {
            'title': 'sequence to sequence',
            'type': 'Seq2seq',
            'image': staticfiles_storage.url('images/tiger-768574_640.jpg'),
            'template_html': 'annotation/seq2seq.html',
            'document_serializer': '',
            'annotations_serializer': '',
        },

        'ImageClassification': {
            'title': 'image classification',
            'type': 'DocumentClassification',
            'image': staticfiles_storage.url('images/cat-1045782_640.jpg'),
            'template_html': 'annotation/image_classification.html',
            'document_serializer': '',
            'annotations_serializer': '',
        },

        'ImageCaptioning': {
            'title': 'image captioning',
            'type': 'Seq2seq',
            'image': staticfiles_storage.url('images/cat-1045782_640.jpg'),
            'template_html': 'annotation/image_captioning.html',
            'document_serializer': '',
            'annotations_serializer': '',
        },

        'AudioLabeling': {
            'title': 'audio labeling',
            'type': 'AudioLabeling',
            'image': staticfiles_storage.url('images/cat-1045782_640.jpg'),
            'template_html': 'annotation/audio_labeling.html',
            'document_serializer': '',
            'annotations_serializer': '',
        },
    }
    DOCUMENT_CLASSIFICATION = 'DocumentClassification'
    SEQUENCE_LABELING = 'SequenceLabeling'
    Seq2seq = 'Seq2seq'
    AUDIO_LABELING = 'AudioLabeling'

    # PROJECT_CHOICES = (
    #     (DOCUMENT_CLASSIFICATION, 'document classification'),
    #     (SEQUENCE_LABELING, 'sequence labeling'),
    #     (Seq2seq, 'sequence to sequence'),
    # )

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


    def get_documents(self, is_null=True, user=None):
        docs = self.documents.all()
        if self.is_type_of(Project.DOCUMENT_CLASSIFICATION):
            if user:
                docs = docs.exclude(doc_annotations__user=user)
            # else:
                # docs = docs.filter(doc_annotations__isnull=is_null)
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
        elif self.is_type_of(Project.AUDIO_LABELING):
            if user:
                docs = docs.exclude(audio_annotations__user=user)
            else:
                docs = docs.filter(audio_annotations__isnull=is_null)
        else:
            print('Project type: '+self.project_type)
            raise ValueError('Invalid project_type')

        return docs

    def get_docs_count(self):
        docs = self.documents.all()
        return len(docs)

    def get_document_serializer(self):
        from .serializers import ClassificationDocumentSerializer
        from .serializers import SequenceDocumentSerializer
        from .serializers import Seq2seqDocumentSerializer
        if self.is_type_of(Project.DOCUMENT_CLASSIFICATION):
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
        elif self.is_type_of(Project.SEQUENCE_LABELING):
            return SequenceAnnotationSerializer
        elif self.is_type_of(Project.Seq2seq):
            return Seq2seqAnnotationSerializer

    def get_annotation_class(self):
        if self.is_type_of(Project.DOCUMENT_CLASSIFICATION):
            return DocumentAnnotation
        elif self.is_type_of(Project.SEQUENCE_LABELING):
            return SequenceAnnotation
        elif self.is_type_of(Project.Seq2seq):
            return Seq2seqAnnotation

    def __str__(self):
        return self.name


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

    class Meta:
        abstract = True

class AnnotationExternal(models.Model):
    prob = models.FloatField(null=True, blank=True, default=None)
    created_date_time = models.DateTimeField(auto_now_add=True)
    updated_date_time = models.DateTimeField(auto_now=True)

    class Meta:
        abstract = True


class DocumentAnnotation(Annotation):
    document = models.ForeignKey(Document, related_name='doc_annotations', on_delete=models.CASCADE)
    label = models.ForeignKey(Label, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('document', 'user', 'label')

class DocumentMLMAnnotation(AnnotationExternal):
    document = models.ForeignKey(Document, related_name='doc_mlm_annotations', on_delete=models.CASCADE)
    label = models.ForeignKey(Label, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('document', 'label')

class DocumentGoldAnnotation(AnnotationExternal):
    document = models.ForeignKey(Document, related_name='doc_gold_annotations', on_delete=models.CASCADE)
    label = models.ForeignKey(Label, on_delete=models.CASCADE)

    class Meta:
        unique_together = ('document', 'label')


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

class AudioAnnotation(Annotation):
    document = models.ForeignKey(Document, related_name='audio_annotations', on_delete=models.CASCADE)
    text = models.TextField()

    class Meta:
        unique_together = ('document', 'user', 'text')
