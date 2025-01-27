# Generated by Django 2.2.7 on 2024-05-13 13:41

import django.core.validators
from django.db import migrations, models
import re


class Migration(migrations.Migration):

    dependencies = [
        ('quiz', '0004_csvupload_title'),
    ]

    operations = [
        migrations.AlterField(
            model_name='progress',
            name='score',
            field=models.CharField(max_length=1024, validators=[django.core.validators.RegexValidator(re.compile('^\\d+(?:,\\d+)*\\Z'), code='invalid', message='Введите только цифры, разделенные запятыми.')], verbose_name='Score'),
        ),
        migrations.AlterField(
            model_name='quiz',
            name='draft',
            field=models.BooleanField(blank=True, default=False, help_text='Если выберите, тест не отображается в списке тестов, и его могут пройти только пользователи, имеющие право редактировать тесты.', verbose_name='Draft'),
        ),
        migrations.AlterField(
            model_name='sitting',
            name='incorrect_questions',
            field=models.CharField(blank=True, max_length=1024, validators=[django.core.validators.RegexValidator(re.compile('^\\d+(?:,\\d+)*\\Z'), code='invalid', message='Введите только цифры, разделенные запятыми.')], verbose_name='Incorrect questions'),
        ),
        migrations.AlterField(
            model_name='sitting',
            name='question_list',
            field=models.CharField(max_length=1024, validators=[django.core.validators.RegexValidator(re.compile('^\\d+(?:,\\d+)*\\Z'), code='invalid', message='Введите только цифры, разделенные запятыми.')], verbose_name='Question List'),
        ),
        migrations.AlterField(
            model_name='sitting',
            name='question_order',
            field=models.CharField(max_length=1024, validators=[django.core.validators.RegexValidator(re.compile('^\\d+(?:,\\d+)*\\Z'), code='invalid', message='Введите только цифры, разделенные запятыми.')], verbose_name='Question Order'),
        ),
    ]
