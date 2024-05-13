import re
import json
import csv
from django.db import models
from django.core.exceptions import ValidationError, ImproperlyConfigured
from django.core.validators import MaxValueValidator, validate_comma_separated_integer_list
from django.utils.timezone import now
from django.conf import settings
from django.utils.translation import ugettext as _
from model_utils.managers import InheritanceManager
from django.db.models.signals import pre_save, post_save
import io
from .signals import csv_uploaded
from .validators import csv_file_validator
from django.contrib.auth.models import User
from django.contrib import messages


class CategoryManager(models.Manager):

    def new_category(self, category):
        new_category = self.create(category=re.sub('\s+', '-', category)
                                   .lower())

        new_category.save()
        return new_category


class Category(models.Model):

    category = models.CharField(
        verbose_name=_("Category"),
        max_length=250, blank=True,
        unique=True, null=True)

    objects = CategoryManager()

    class Meta:
        verbose_name = _("Category")
        verbose_name_plural = _("Categories")

    def __str__(self):
        return self.category


class Quiz(models.Model):

    title = models.CharField(
        verbose_name=_("Title"),
        max_length=60, blank=False)

    description = models.TextField(
        verbose_name=_("Description"),
        blank=True, help_text=_("описание теста"))

    url = models.SlugField(
        max_length=60, blank=False,
        help_text=_("URL ваш"),
        verbose_name=_("user friendly url"))

    category = models.ForeignKey(
        Category, null=True, blank=True,
        verbose_name=_("Category"), on_delete=models.CASCADE)

    random_order = models.BooleanField(
        blank=False, default=False,
        verbose_name=_("Random Order"),
        help_text=_("Отобразите вопросы в "
                    "в случайном порядке или по мере того, как они "
                    "=установлены?"))

    max_questions = models.PositiveIntegerField(
        blank=True, null=True, verbose_name=_("Max Questions"),
        help_text=_("Количество вопросов, на которые необходимо ответить при каждой попытке."))

    answers_at_end = models.BooleanField(
        blank=False, default=False,
        help_text=_("Правильный ответ НЕ отображается после вопроса."
                    " Ответы отображаются в конце."),
        verbose_name=_("Answers at end"))

    exam_paper = models.BooleanField(
        blank=False, default=False,
        help_text=_("Если да, то результат каждого"
                    " попытка пользователя будет"
                    " хранится. Необходимо для маркировки."),
        verbose_name=_("Exam Paper"))

    single_attempt = models.BooleanField(
        blank=False, default=False,
        help_text=_("Если да, то только одна попытка"
                    " пользователю будет разрешено."
                    " Непользователи не могут сдавать этот экзамен."),
        verbose_name=_("Single Attempt"))

    pass_mark = models.SmallIntegerField(
        blank=True, default=0,
        verbose_name=_("Pass Mark"),
        help_text=_("Процент, необходимый для сдачи экзамена."),
        validators=[MaxValueValidator(100)])

    success_text = models.TextField(
        blank=True, help_text=_("Отображается, если пользователь проходит."),
        verbose_name=_("Success Text"))

    fail_text = models.TextField(
        verbose_name=_("Fail Text"),
        blank=True, help_text=_("Отображается в случае сбоя пользователя."))

    draft = models.BooleanField(
        blank=True, default=False,
        verbose_name=_("Draft"),
        help_text=_("Если да, то тест не отображается"
                    " в списке тест и может быть только"
                    " снято пользователями, которые могут редактировать"
                    " quizzes."))

    def save(self, force_insert=False, force_update=False, *args, **kwargs):
        self.url = re.sub('\s+', '-', self.url).lower()

        self.url = ''.join(letter for letter in self.url if
                           letter.isalnum() or letter == '-')

        if self.single_attempt is True:
            self.exam_paper = True

        if self.pass_mark > 100:
            raise ValidationError('%s от 100' % self.pass_mark)

        super(Quiz, self).save(force_insert, force_update, *args, **kwargs)

    class Meta:
        verbose_name = _("Quiz")
        verbose_name_plural = _("Quizzes")

    def __str__(self):
        return self.title

    def get_questions(self):
        return self.question_set.all().select_subclasses()

    @property
    def get_max_score(self):
        return self.get_questions().count()

    def anon_score_id(self):
        return str(self.id) + "_score"

    def anon_q_list(self):
        return str(self.id) + "_q_list"

    def anon_q_data(self):
        return str(self.id) + "_data"


# progress manager
class ProgressManager(models.Manager):

    def new_progress(self, user):
        new_progress = self.create(user=user,
                                   score="")
        new_progress.save()
        return new_progress


class Progress(models.Model):
    """
    Прогресс используется для отслеживания результатов отдельных вошедших в систему пользователей на различных
     викторины и категории
     Данные хранятся в csv в формате:
        category, score, possible, category, score, possible, ...
    """
    user = models.OneToOneField(settings.AUTH_USER_MODEL, verbose_name=_("User"), on_delete=models.CASCADE)

    score = models.CharField(validators=[validate_comma_separated_integer_list], max_length=1024,
                                              verbose_name=_("Score"))

    correct_answer = models.CharField(max_length=10, verbose_name=_('Correct Answers'))

    wrong_answer = models.CharField(max_length=10, verbose_name=_('Wrong Answers')) 

    objects = ProgressManager()

    class Meta:
        verbose_name = _("User Progress")
        verbose_name_plural = _("User progress records")

    @property
    def list_all_cat_scores(self):
        """
        Возвращает словарь, в котором ключом является имя категории, а элементом
         список из трех целых чисел.
         Во-первых, это количество правильных вопросов,
         второй - возможный лучший результат,
         третий — процент правильных ответов.
         В словаре будет один ключ для каждой определенной вами категории.
        """
        score_before = self.score
        output = {}

        for cat in Category.objects.all():
            to_find = re.escape(cat.category) + r",(\d+),(\d+),"
            #  group 1 is score, group 2 is highest possible

            match = re.search(to_find, self.score, re.IGNORECASE)

            if match:
                score = int(match.group(1))
                possible = int(match.group(2))

                try:
                    percent = int(round((float(score) / float(possible))
                                        * 100))
                except:
                    percent = 0

                output[cat.category] = [score, possible, percent]

            else:  # if category has not been added yet, add it.
                self.score += cat.category + ",0,0,"
                output[cat.category] = [0, 0]

        if len(self.score) > len(score_before):
            # If a new category has been added, save changes.
            self.save()

        return output

    def update_score(self, question, score_to_add=0, possible_to_add=0):
        """
       Передайте вопросительный объект, укажите сумму для увеличения счета
         и максимально возможное.
         Ничего не возвращает.
        """
        category_test = Category.objects.filter(category=question.category)\
                                        .exists()

        if any([item is False for item in [category_test,
                                           score_to_add,
                                           possible_to_add,
                                           isinstance(score_to_add, int),
                                           isinstance(possible_to_add, int)]]):
            return _("error"), _("category does not exist or invalid score")

        to_find = re.escape(str(question.category)) +\
            r",(?P<score>\d+),(?P<possible>\d+),"

        match = re.search(to_find, self.score, re.IGNORECASE)

        if match:
            updated_score = int(match.group('score')) + abs(score_to_add)
            updated_possible = int(match.group('possible')) +\
                abs(possible_to_add)

            new_score = ",".join(
                [
                    str(question.category),
                    str(updated_score),
                    str(updated_possible), ""
                ])

            # swap old score for the new one
            self.score = self.score.replace(match.group(), new_score)
            self.save()

        else:
            #  if not present but existing, add with the points passed in
            self.score += ",".join(
                [
                    str(question.category),
                    str(score_to_add),
                    str(possible_to_add),
                    ""
                ])
            self.save()

    def show_exams(self):
        """
Находит предыдущие тесты, помеченные как «экзаменационные работы».
         Возвращает набор запросов полных экзаменов.
        """
        return Sitting.objects.filter(user=self.user, complete=True)

    def __str__(self):
        return self.user.username + ' - '  + self.score


class SittingManager(models.Manager):

    def new_sitting(self, user, quiz):
        if quiz.random_order is True:
            question_set = quiz.question_set.all() \
                                            .select_subclasses() \
                                            .order_by('?')
        else:
            question_set = quiz.question_set.all() \
                                            .select_subclasses()

        question_set = [item.id for item in question_set]

        if len(question_set) == 0:
            raise ImproperlyConfigured('Question set of the quiz is empty. '
                                       'Please configure questions properly')

        if quiz.max_questions and quiz.max_questions < len(question_set):
            question_set = question_set[:quiz.max_questions]

        questions = ",".join(map(str, question_set)) + ","

        new_sitting = self.create(user=user,
                                  quiz=quiz,
                                  question_order=questions,
                                  question_list=questions,
                                  incorrect_questions="",
                                  current_score=0,
                                  complete=False,
                                  user_answers='{}')
        return new_sitting

    def user_sitting(self, user, quiz):
        if quiz.single_attempt is True and self.filter(user=user,
                                                       quiz=quiz,
                                                       complete=True)\
                                               .exists():
            return False

        try:
            sitting = self.get(user=user, quiz=quiz, complete=False)
        except Sitting.DoesNotExist:
            sitting = self.new_sitting(user, quiz)
        except Sitting.MultipleObjectsReturned:
            sitting = self.filter(user=user, quiz=quiz, complete=False)[0]
        return sitting


class Sitting(models.Model):
    """
   Используется для хранения прогресса вошедших в систему пользователей, проходящих викторину.
     Заменяет систему сеансов, используемую анонимными пользователями.
     Вопрос_order — это список целочисленных блоков всех вопросов в
     викторина по порядку.
     Вопрос_список — это список целых чисел, представляющих идентификаторы
     вопросы без ответов в формате csv.
     Incorrect_questions — это список в том же формате.
     Сидение удаляется после завершения теста, если значение quiz.exam_paper не равно true.
     User_ответы — это объект json, в котором хранится вопрос PK.
     с ответом, который дал пользователь.
    """

    user = models.ForeignKey(settings.AUTH_USER_MODEL, verbose_name=_("User"), on_delete=models.CASCADE)

    quiz = models.ForeignKey(Quiz, verbose_name=_("Quiz"), on_delete=models.CASCADE)

    question_order = models.CharField(validators=[validate_comma_separated_integer_list],
        max_length=1024, verbose_name=_("Question Order"))

    question_list = models.CharField(validators=[validate_comma_separated_integer_list],
        max_length=1024, verbose_name=_("Question List"))

    incorrect_questions = models.CharField(validators=[validate_comma_separated_integer_list],
        max_length=1024, blank=True, verbose_name=_("Incorrect questions"))

    current_score = models.IntegerField(verbose_name=_("Current Score"))

    complete = models.BooleanField(default=False, blank=False,
                                   verbose_name=_("Complete"))

    user_answers = models.TextField(blank=True, default='{}',
                                    verbose_name=_("User Answers"))

    start = models.DateTimeField(auto_now_add=True,
                                 verbose_name=_("Start"))

    end = models.DateTimeField(null=True, blank=True, verbose_name=_("End"))

    objects = SittingManager()

    class Meta:
        permissions = (("view_sittings", _("Can see completed exams.")),)

    def get_first_question(self):
        """
       Возвращает следующий вопрос.
         Если вопрос не найден, возвращается False
         НЕ удаляет вопрос из начала списка.
        """
        if not self.question_list:
            return False

        first, _ = self.question_list.split(',', 1)
        question_id = int(first)
        return Question.objects.get_subclass(id=question_id)

    def remove_first_question(self):
        if not self.question_list:
            return

        _, others = self.question_list.split(',', 1)
        self.question_list = others
        self.save()

    def add_to_score(self, points):
        self.current_score += int(points)
        self.save()

    @property
    def get_current_score(self):
        return self.current_score

    def _question_ids(self):
        return [int(n) for n in self.question_order.split(',') if n]

    @property
    def get_percent_correct(self):
        dividend = float(self.current_score)
        divisor = len(self._question_ids())
        if divisor < 1:
            return 0            # prevent divide by zero error

        if dividend > divisor:
            return 100

        correct = int(round((dividend / divisor) * 100))

        if correct >= 1:
            return correct
        else:
            return 0

    def mark_quiz_complete(self):
        self.complete = True
        self.end = now()
        self.save()

    def add_incorrect_question(self, question):
        """
Добавляет в список идентификатор неправильного вопроса.
         Объект вопроса должен быть передан.
        """
        if len(self.incorrect_questions) > 0:
            self.incorrect_questions += ','
        self.incorrect_questions += str(question.id) + ","
        if self.complete:
            self.add_to_score(-1)
        self.save()

    @property
    def get_incorrect_questions(self):
        """
Возвращает список непустых целых чисел, представляющих ПК
         вопросы
        """
        return [int(q) for q in self.incorrect_questions.split(',') if q]

    def remove_incorrect_question(self, question):
        current = self.get_incorrect_questions
        current.remove(question.id)
        self.incorrect_questions = ','.join(map(str, current))
        self.add_to_score(1)
        self.save()

    @property
    def check_if_passed(self):
        return self.get_percent_correct >= self.quiz.pass_mark

    @property
    def result_message(self):
        if self.check_if_passed:
            return self.quiz.success_text
        else:
            return self.quiz.fail_text

    def add_user_answer(self, question, guess):
        current = json.loads(self.user_answers)
        current[question.id] = guess
        self.user_answers = json.dumps(current)
        self.save()

    def get_questions(self, with_answers=False):
        question_ids = self._question_ids()
        questions = sorted(
            self.quiz.question_set.filter(id__in=question_ids)
                                  .select_subclasses(),
            key=lambda q: question_ids.index(q.id))

        if with_answers:
            user_answers = json.loads(self.user_answers)
            for question in questions:
                question.user_answer = user_answers[str(question.id)]

        return questions

    @property
    def questions_with_user_answers(self):
        return {
            q: q.user_answer for q in self.get_questions(with_answers=True)
        }

    @property
    def get_max_score(self):
        return len(self._question_ids())

    def progress(self):
        """
Возвращает количество вопросов, на которые на данный момент даны ответы, и общее количество
         вопросы.
        """
        answered = len(json.loads(self.user_answers))
        total = self.get_max_score
        return answered, total


class Question(models.Model):
    """
Базовый класс для всех типов вопросов.
     Общие объекты недвижимости размещены здесь.
    """

    quiz = models.ManyToManyField(Quiz,
                                  verbose_name=_("Quiz"),
                                  blank=True)

    category = models.ForeignKey(Category,
                                 verbose_name=_("Category"),
                                 blank=True,
                                 null=True, on_delete=models.CASCADE)

    figure = models.ImageField(upload_to='uploads/%Y/%m/%d',
                               blank=True,
                               null=True,
                               verbose_name=_("Figure"))

    content = models.CharField(max_length=1000,
                               blank=False,
                               help_text=_("Введите текст вопроса, который "
                                           "вы хотите отобразить"),
                               verbose_name=_('Question'))

    explanation = models.TextField(max_length=2000,
                                   blank=True,
                                   help_text=_("Пояснение, которое будет показано "
                                               "после того, как вопрос был "
                                               "был дан ответ."),
                                   verbose_name=_('Explanation'))

    objects = InheritanceManager()

    class Meta:
        verbose_name = _("Question")
        verbose_name_plural = _("Questions")
        ordering = ['category']

    def __str__(self):
        return self.content


def upload_csv_file(instance, filename):
    qs = instance.__class__.objects.filter(user=instance.user)
    if qs.exists():
        num_ = qs.last().id + 1
    else:
        num_ = 1
    return f'csv/{num_}/{instance.user.username}/{filename}'


class CSVUpload(models.Model):
    title       = models.CharField(max_length=100, verbose_name=_('Title'), blank=False)
    user        = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file        = models.FileField(upload_to=upload_csv_file, validators=[csv_file_validator])
    completed   = models.BooleanField(default=False)
    # questions   = models.BooleanField(default=True)
    # students    = models.BooleanField(default=False)

    def __str__(self):
        return self.user.username

def create_user(data):
    user =  User.objects.create_user(username=data['username'], 
                            email=data['email'],
                            password=data['password'],
                            first_name=data['first_name'],
                            last_name=data['last_name']
                            )
    user.is_admin=False
    user.is_staff=False
    user.save()


def convert_header(csvHeader):
    header_ = csvHeader[0]
    cols = [x.replace(' ', '_').lower() for x in header_.split(",")]
    return cols


def csv_upload_post_save(sender, instance, created, *args, **kwargs):
    if not instance.completed:
        csv_file = instance.file
        decoded_file = csv_file.read().decode('utf-8')
        io_string = io.StringIO(decoded_file)
        reader = csv.reader(io_string, delimiter=';', quotechar='|')
        header_ = next(reader)
        header_cols = convert_header(header_)
        print(header_cols, str(len(header_cols)))
        parsed_items = []

#           джанго ишет условие
        '''
        if using a custom signal
        '''
        for line in reader:
            # print(line)
            parsed_row_data = {}
            i = 0
            print(line[0].split(','), len(line[0].split(',')))
            row_item = line[0].split(',')
            for item in row_item:
                key = header_cols[i]
                parsed_row_data[key] = item
                i+=1
            create_user(parsed_row_data) # create user
            parsed_items.append(parsed_row_data)
            # messages.success(parsed_items)
            print(parsed_items)
        csv_uploaded.send(sender=instance, user=instance.user, csv_file_list=parsed_items)
        ''' 
        если использовать модель напрямую
        for line in reader:
            new_obj = YourModelKlass()
            i = 0
            row_item = line[0].split(',')
            for item in row_item:
                key = header_cols[i]
                setattr(new_obj, key) = item
                i+=1
            new_obj.save()
        ''' 
        instance.completed = True
        instance.save()


post_save.connect(csv_upload_post_save, sender=CSVUpload)


