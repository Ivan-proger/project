# Generated by Django 5.0 on 2024-02-21 18:16

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bot1', '0023_alter_users_name'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='series',
            name='genres',
        ),
        migrations.DeleteModel(
            name='Genre',
        ),
    ]
