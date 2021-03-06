# Generated by Django 2.1.5 on 2019-02-13 01:01

from django.db import migrations, models
import django.utils.timezone


class Migration(migrations.Migration):

    dependencies = [
        ('server', '0003_shortcut'),
    ]

    operations = [
        migrations.AddField(
            model_name='document',
            name='created_date_time',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='document',
            name='updated_date_time',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='documentannotation',
            name='created_date_time',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='documentannotation',
            name='updated_date_time',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='seq2seqannotation',
            name='created_date_time',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='seq2seqannotation',
            name='updated_date_time',
            field=models.DateTimeField(auto_now=True),
        ),
        migrations.AddField(
            model_name='sequenceannotation',
            name='created_date_time',
            field=models.DateTimeField(auto_now_add=True, default=django.utils.timezone.now),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='sequenceannotation',
            name='updated_date_time',
            field=models.DateTimeField(auto_now=True),
        ),
    ]
