from re import compile
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models import QuerySet, Value, Q, F, When, Case, Max, OuterRef
from django.utils import timezone


class UserManager(BaseUserManager):

    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('نام کاربری باید وارد شود.')
            # the exception message is provided in farsi
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(username, password, **extra_fields)


class User(AbstractUser):
    phone_number = models.CharField(max_length=11, unique=True, blank=True, null=True)

    profile_image = models.ImageField(
        upload_to='profile_pics/',
        verbose_name='Profile Image',
        null=True,
        help_text='image for profile of user'
    )

    email = None  # email field is substitute with phone_number
    EMAIL_FIELD = 'phone_number'
    REQUIRED_FIELDS = []
    objects = UserManager()

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"

    @property
    def is_manager(self) -> bool:
        """
            provided for api app
            :returns: true if user is superuser or staff.
        """
        return self.is_superuser or self.is_staff

    @is_manager.setter
    def is_manager(self, value: bool):
        """ only sets the is_staff attribute.
            HINT: to change is_superuser column go to the admin site.
        """
        self.is_staff = value


class Automobile(models.Model):
    plate = models.CharField(max_length=20, primary_key=True)

    # most of these fields are nullable for anonymous Automobiles.
    color = models.CharField(max_length=64, null=True, blank=True)
    name_and_model = models.CharField(max_length=128, null=True, blank=True)
    owner_first_name = models.CharField(max_length=128, null=True, blank=True)
    owner_last_name = models.CharField(max_length=128, null=True, blank=True)
    owner_username = models.CharField(max_length=128, null=True, blank=True)
    # owner_username could be any unique code or name for identification.

    is_allways_permitted = models.BooleanField(default=False)

    PLATE_PATTERN = r"\d{2}-[آ-ی]-\d{3}-\d{2}"
    FULL_MATCH_PLATE_PATTERN = r'^' + PLATE_PATTERN + r'$'

    class Meta:
        unique_together = (('plate', 'owner_username'),)

    @staticmethod
    def is_permitted_conditions() -> Q:

        now = timezone.now()
        return (Q(is_allways_permitted=True) |
                (Q(permissions__to_time__gt=now) & Q(permissions__from_time__lte=now)))

    def get_active_permission(self) -> 'TemporaryPermission':
        return self.permissions.filter(
            Q(to_time__gt=timezone.now()) & Q(from_time__lte=timezone.now())
        ).order_by('to_time').first()

    @staticmethod
    def is_anonymous_conditions() -> Q:
        return (~Automobile.is_permitted_conditions() &
                (Q(owner_username__isnull=True) & Q(owner_first_name__isnull=True) & Q(owner_last_name__isnull=True)) &
                (Q(color__isnull=True) & Q(name_and_model__isnull=True)))

    @staticmethod
    def get_annotated_is_permitted(query_set: QuerySet['Automobile']) -> QuerySet['Automobile']:
        """
        :param query_set: given query set to be annotated.
        :return: annotated query set with is_permitted to true if automobile has is_permitted_conditions else false.
        """

        not_distinct_annotated = query_set.annotate(
            is_permitted=Case(
                When(
                    Automobile.is_permitted_conditions(),
                    then=Value(True)
                ),
                default=Value(False),
                output_field=models.BooleanField()
            )
        )
        distinct_with_correct_value_of_is_permitted = not_distinct_annotated.annotate(
            is_permitted=Max('is_permitted')  # to return true if any exist else false for is_permitted
        )
        return distinct_with_correct_value_of_is_permitted

    def __repr__(self):
        return (f'Automobile({self.plate= }, '
                f' {self.name_and_model= }, '
                f' {self.color= }, '
                f' {self.owner_username= }, {self.owner_first_name= }, {self.owner_last_name= }, '
                f' {self.is_allways_permitted= }, '
                f')')

    def __str__(self):
        return self.__repr__()


class TemporaryPermission(models.Model):
    automobile = models.ForeignKey(Automobile, on_delete=models.CASCADE, related_name='permissions')

    from_time = models.DateTimeField(default=timezone.now)
    to_time = models.DateTimeField()
    description = models.TextField(default="بدون توضیحات")

    @staticmethod
    def active_permission_condition_for(automobile: Automobile) -> Q:

        now = timezone.now()
        return Q(automobile=automobile) & (Q(to_time__gt=now) & Q(from_time__lte=now))

    @staticmethod
    def conflict_with_current_or_future_permissions_conditions(
            new_permission: 'TemporaryPermission'
    ) -> Q:
        """
        :param new_permission: permission to check these conditions on it.
        :return: Q() object that represent conflict with current or future permissions.
        """
        now = timezone.now()
        conflict_condition = (
                Q(
                    automobile=new_permission.automobile,
                    from_time__lt=new_permission.to_time,  # check any permission starts before end of new permission
                    to_time__gt=new_permission.from_time,  # check any permission ends after start of new permission
                )
                &
                Q(to_time__gt=now)
                )  # check for active or current permissions

        if new_permission.pk is not None:
            # Exclude the new_permission itself if it exists (update/partial update scenarios)
            conflict_condition &= ~Q(pk=new_permission.pk)

        return conflict_condition


class Place(models.Model):
    name = models.CharField(max_length=64, unique=True)
    security = models.ManyToManyField(to=User, through='api.SecurityAssignment', related_name='secured_gates')


class Gate(models.Model):
    name = models.CharField(max_length=64, unique=True)
    type = models.CharField(
        max_length=20,
        choices=[
            ("enter", "ورودی"),
            ("exit", "خروجی"),
        ],
        default="enter",
    )

    class Meta:
        unique_together = (('name', 'type'),)

    permission_needed = models.BooleanField(default=True)

    place = models.ForeignKey(Place, on_delete=models.CASCADE, related_name='gates')

    traffics = models.ManyToManyField(to=Automobile, through='api.Traffic', related_name='passed_gates', )


def auto_traffic_image(instance, filename):
    """
    :return: string represents path of storage for traffic images
            in format : traffic_pics/{plate}-{time of traffic}-{type of traffic (enter or exit)}-{filename}
    """
    return f'traffic_pics/{instance.automobile.plate}-{instance.time}-{instance.gate.type}-{filename}'


class Traffic(models.Model):
    automobile = models.ForeignKey(to=Automobile, on_delete=models.RESTRICT,)
    gate = models.ForeignKey(to=Gate, on_delete=models.RESTRICT,)
    image = models.ImageField(upload_to=auto_traffic_image, )
    time = models.DateTimeField()
    security_agent = models.ForeignKey(to=User, on_delete=models.RESTRICT, related_name='traffics')

    class Meta:
        ordering = ('-time',)


class SecurityAssignment(models.Model):
    security_agent = models.ForeignKey(to=User, on_delete=models.RESTRICT,)
    place = models.ForeignKey(to=Place, on_delete=models.RESTRICT,)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()

    class Meta:
        ordering = ('-start_time',)

