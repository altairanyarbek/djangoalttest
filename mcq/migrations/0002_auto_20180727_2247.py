
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mcq', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='mcqquestion',
            name='answer_order',
            field=models.CharField(blank=True, choices=[('content', 'Content'), ('none', 'None')], help_text='Порядок, в котором множественный выбор                     отображаются варианты ответа                     пользователю', max_length=30, null=True, verbose_name='Answer Order'),
        ),
    ]
