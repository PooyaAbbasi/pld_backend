from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager


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
        verbose_name='Profile Image', null=True,
        help_text='image for profile of user'
    )

    email = None  # email field is substitute with phone_number
    EMAIL_FIELD = 'phone_number'
    REQUIRED_FIELDS = []
    objects = UserManager()

    class Meta:
        verbose_name = "User"
        verbose_name_plural = "Users"
