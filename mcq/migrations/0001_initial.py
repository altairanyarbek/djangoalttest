
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('quiz', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='Answer',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('content', models.CharField(help_text='Введите текст ответа, который                                            вы хотите отобразить', max_length=1000, verbose_name='Content')),
                ('correct', models.BooleanField(default=False, help_text='Это правильный ответ?', verbose_name='Correct')),
            ],
            options={
                'verbose_name': 'Answer',
                'verbose_name_plural': 'Answers',
            },
        ),
        migrations.CreateModel(
            name='MCQQuestion',
            fields=[
                ('question_ptr', models.OneToOneField(auto_created=True, on_delete=django.db.models.deletion.CASCADE, parent_link=True, primary_key=True, serialize=False, to='quiz.Question')),
                ('answer_order', models.CharField(blank=True, choices=[('content', 'Content'), ('random', 'Random'), ('none', 'None')], help_text='Порядок, в котором множественный выбор                     отображаются варианты ответа                     пользователю', max_length=30, null=True, verbose_name='Answer Order')),
            ],
            options={
                'verbose_name': 'Multiple Choice Question',
                'verbose_name_plural': 'Multiple Choice Questions',
            },
            bases=('quiz.question',),
        ),
        migrations.AddField(
            model_name='answer',
            name='question',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='mcq.MCQQuestion', verbose_name='Question'),
        ),
    ]
