# Generated by Django 2.1.5 on 2019-05-14 15:39

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('server', '0015_auto_20190514_1534'),
    ]

    operations = [
        migrations.RenameField(
            model_name='project',
            old_name='show_predicted',
            new_name='show_ml_model_prediction',
        ),
    ]
