from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db import models


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


class Automobile(models.Model):
    plate = models.CharField(max_length=20, primary_key=True)

    # most of these fields are nullable for anonymous Automobiles.
    color = models.CharField(max_length=64, null=True)
    name_and_model = models.CharField(max_length=128, null=True)
    owner_first_name = models.CharField(max_length=128, null=True)
    owner_last_name = models.CharField(max_length=128, null=True)
    owner_username = models.CharField(max_length=128, null=True)
    # owner_username could be any unique code or name for identification.

    is_allways_permitted = models.BooleanField(default=False)

    class Meta:
        unique_together = (('plate', 'owner_username'),)


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
    automobile = models.ForeignKey(to=Automobile, on_delete=models.CASCADE, )
    gate = models.ForeignKey(to=Gate, on_delete=models.CASCADE,)
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

