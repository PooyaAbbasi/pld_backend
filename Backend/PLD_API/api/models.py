from re import compile
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models
from django.db.models import QuerySet, Value, Q, F, When, Case
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
        print(f'in is_manager setter value{value}')
        self.is_staff = value
        # self.save(update_fields=['is_staff'])


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

    def is_permitted(self) -> bool:
        """
        :return: true if automobile.is_allways_permitted
                or has a valid related TemporaryPermission for now.

        HINT: Doesn't efficient for database query it's just for development,
            Use .filter with is_permitted_conditions() static method to get this attribute.
        TODO Should be removed for production.
        """

        # last temporary permission of this automobile
        temp_permission: TemporaryPermission = self.get_last_temp_permission()
        if self.is_allways_permitted:
            return True
        elif temp_permission is not None:
            return temp_permission.from_time <= timezone.now() <= temp_permission.to_time

        # No permission found
        return False

    def get_last_temp_permission(self) -> 'TemporaryPermission':
        """
        :returns: first temporary permission object related to this automobile which are ordered by to_time descending.
        HINT: Doesn't efficient for database query it's just for development,
        TODO Should be removed for production.
        """
        return self.permissions.order_by('-to_time').first()

        # I don't know wich one is more efficient. (- _ -)
        # >>> max_to_time = self.permissions.aggrigate(max_to_time=models.Max('to_time'))['max_to_time']
        # >>> return self.permissions.first(to_time=max_to_time).first()

    def is_anonymous(self) -> bool:
        """
        :return: true if automobile is not permitted or not have saved owner info or name_and_model
        """

        anonymous_conditions: tuple[bool, bool, bool] = (
            not self.is_permitted,
            (self.owner_username is None) and (self.owner_first_name is None and self.owner_last_name is None),
            self.name_and_model is None
        )

        return all(anonymous_conditions)

    @staticmethod
    def is_permitted_conditions() -> Q:
        return Q(is_allways_permitted=True) | Q(permissions__to_time__gt=timezone.now())

    @staticmethod
    def is_anonymous_conditions() -> Q:
        return (~Automobile.is_permitted_conditions() &
                (Q(owner_username__isnull=True) & Q(owner_first_name__isnull=True) & Q(owner_last_name__isnull=True)) &
                (Q(color__isnull=True) & Q(name_and_model__isnull=True)))

    @staticmethod
    def get_annotated_is_permitted(query_set: QuerySet['Automobile']) -> QuerySet['Automobile']:
        """
        :param query_set: given query set to be annotated.
        :return: annotated query set with is_permitted to true if automobile has is_permitted_conditions.
        """
        return query_set.annotate(
            is_permitted=Case(
                When(Automobile.is_permitted_conditions(), then=Value(True)),
                default=Value(False),
                output_field=models.BooleanField()
            )
        )

    def __repr__(self):
        return (f'Automobile({self.plate= }, '
                f' {self.name_and_model= }, '
                f' {self.color= }, '
                f' {self.owner_username= }, {self.owner_first_name= }, {self.owner_last_name= }, '
                f' {self.is_allways_permitted= }, '
                f' {self.is_permitted()= }'
                f'{self.is_anonymous()= }'
                f')')

    def __str__(self):
        return self.__repr__()


class TemporaryPermission(models.Model):
    automobile = models.ForeignKey(Automobile, on_delete=models.CASCADE, related_name='permissions')

    from_time = models.DateTimeField(auto_now_add=True, )
    to_time = models.DateTimeField()
    description = models.TextField(default="بدون توضیحات")


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

