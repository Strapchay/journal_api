from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.conf import settings
from django.db.models.constraints import UniqueConstraint
from django.db.models import Q
import random
import string


# Create your models here.
class UserManager(BaseUserManager):
    """
    Manager for User Model
    """

    def create_user(self, email, password, **extra_fields):
        """
        Create and return a new Useer without privileges
        """
        if not email:
            raise ValueError("User must have an email address")
        user = self.model(email=self.normalize_email(email), **extra_fields)
        user.set_password(password)
        user.save(using=self.db)
        return user

    def create_superuser(self, email, password):
        """
        Create and return a superuser
        """
        user = self.create_user(email, password)
        user.is_staff = True
        user.is_superuser = True
        user.save(using=self.db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    """
    User Model
    """

    email = models.EmailField(max_length=255, unique=True)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    username = models.CharField(max_length=40, null=True, blank=True)
    is_active = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"

    def gen_rand_name(self):
        chars = string.ascii_letters
        rand_name = "".join(random.choice(chars) for x in range(4))
        return rand_name

    @property
    def create_username(self):
        username = self.first_name + self.gen_rand_name()
        self.username = username

    def save(self, *args, **kwargs):
        if self.username is not None:
            self.create_username
        super(User, self).save(*args, **kwargs)


class Journal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    journal_name = models.CharField(max_length=200, null=True, blank=True)
    journal_description = models.CharField(max_length=3000, blank=True, null=True)

    def __str__(self) -> str:
        return self.journal_name


class JournalTables(models.Model):
    journal = models.ForeignKey(Journal, on_delete=models.CASCADE)
    table_name = models.CharField(max_length=100)

    def __str__(self) -> str:
        return self.table_name


class Activities(models.Model):
    name = models.CharField(max_length=100)
    created = models.DateTimeField(auto_now=True)
    # tags = models.ForeignKey(Tags, on_delete=models.DO_NOTHING, null=True, blank=True)
    journal_table = models.ForeignKey(
        JournalTables, on_delete=models.CASCADE, null=True, blank=True
    )

    def __str__(self) -> str:
        return self.name


class Tags(models.Model):
    class Colors(models.TextChoices):
        GRAY = "OFF GRAY", "Off Gray"
        GREEN = "MIDNIGHT GREEN", "Midnight Green"
        RED = "WINE RED", "Wine Red"
        ARMY_GREEN = "ARMY GREEN", "Army Green"
        YELLOW = "YELLOW", "Yellow"
        BLUE = "LIGHT BLUE", "Light Blue"
        PEACH = "PEACH", "Peach"
        TEAL = "TEAL", "Teal"
        PURPLE = "PURPLE", "Purple"
        BROWN = "BROWN", "Brown"

    class ColorsClasses(models.TextChoices):
        GRAY_CLASS = "color-gray"
        GREEN_CLASS = "color-green"
        RED_CLASS = "color-red"
        ARMY_GREEN_CLASS = "color-army-green"
        YELLOW_CLASS = "color-yellow"
        BLUE_CLASS = "color-blue"
        PEACH_CLASS = "color-peach"
        TEAL_CLASS = "color-teal"
        PURPLE_CLASS = "color-purple"
        BROWN_CLASS = "color-brown"

    tag_user = models.ForeignKey(
        User, on_delete=models.CASCADE, null=True, blank=True, related_name="tags"
    )
    tag_name = models.CharField(max_length=300)
    tag_color = models.CharField(max_length=30, choices=Colors.choices)
    tag_class = models.CharField(max_length=30, choices=ColorsClasses.choices)
    activities = models.ManyToManyField(
        Activities,
        null=True,
        blank=True,
        # on_delete=models.DO_NOTHING,
        related_name="tags",
    )

    # def save(self,*args,**kwargs):
    # check_unique_val =

    class Meta:
        constraints = (
            UniqueConstraint(
                fields=["tag_user", "tag_name"],
                name="unique_tag_name",
            ),
        )

    def __str__(self) -> str:
        return self.tag_name

    # intention = models.ForeignKey(Intentions, on_delete=models.DO_NOTHING)
    # happening = models.ForeignKey(Happenings, on_delete=models.DO_NOTHING)
    # grateful_for = models.ForeignKey(GratefulFor, on_delete=models.DO_NOTHING)
    # action_item = models.ForeignKey(ActionItems, on_delete=models.DO_NOTHING)


class Intentions(models.Model):
    intention = models.CharField(max_length=2000)
    activity = models.ForeignKey(
        Activities, null=True, blank=True, on_delete=models.CASCADE
    )

    def __str__(self) -> str:
        return self.intention


class Happenings(models.Model):
    happening = models.CharField(max_length=2000)
    activity = models.ForeignKey(
        Activities, null=True, blank=True, on_delete=models.CASCADE
    )

    def __str__(self) -> str:
        return self.happening


class GratefulFor(models.Model):
    grateful_for = models.CharField(max_length=2000)
    activity = models.ForeignKey(
        Activities, null=True, blank=True, on_delete=models.CASCADE
    )

    def __str__(self) -> str:
        return self.grateful_for


class ActionItems(models.Model):
    action_items = models.CharField(max_length=2000)
    activity = models.ForeignKey(
        Activities, null=True, blank=True, on_delete=models.CASCADE
    )

    def __str__(self) -> str:
        return self.action_items
