# Generated by Django 5.0 on 2024-03-17 13:20

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('bot1', '0029_users_ref_code'),
    ]

    operations = [
        migrations.AlterField(
            model_name='users',
            name='ref_code',
            field=models.CharField(blank=True, default=None, max_length=20, null=True, verbose_name='Код рефералки'),
        ),
    ]
