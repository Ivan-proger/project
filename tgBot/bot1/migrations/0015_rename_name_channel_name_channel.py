# Generated by Django 5.0 on 2024-02-12 15:06

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bot1', '0014_alter_channel_name'),
    ]

    operations = [
        migrations.RenameField(
            model_name='channel',
            old_name='name',
            new_name='name_channel',
        ),
    ]
