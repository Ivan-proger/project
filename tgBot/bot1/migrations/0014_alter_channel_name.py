# Generated by Django 5.0 on 2024-02-12 15:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot1', '0013_channel_name'),
    ]

    operations = [
        migrations.AlterField(
            model_name='channel',
            name='name',
            field=models.TextField(blank=True, default='channel', max_length=64, null=True),
        ),
    ]
