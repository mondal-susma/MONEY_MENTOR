# Generated by Django 3.1.3 on 2021-02-05 12:59

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('dashboard', '0011_auto_20210202_1400'),
    ]

    operations = [
        migrations.AddField(
            model_name='stockholding',
            name='company_symbol',
            field=models.CharField(default='', max_length=25),
        ),
    ]
