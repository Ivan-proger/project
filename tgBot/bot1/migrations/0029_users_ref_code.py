# Generated by Django 5.0 on 2024-03-17 13:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot1', '0028_statisticref'),
    ]

    operations = [
        migrations.AddField(
            model_name='users',
            name='ref_code',
            field=models.CharField(default='', max_length=20, verbose_name='Код рефералки'),
        ),
    ]
