# Generated by Django 5.0 on 2024-02-12 15:08

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('bot1', '0015_rename_name_channel_name_channel'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='channel',
            name='name_channel',
        ),
    ]
