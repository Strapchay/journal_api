from django.db import models
from django.contrib.auth.models import (
    AbstractBaseUser,
    BaseUserManager,
    PermissionsMixin,
)
from django.conf import settings
from django.db.models.constraints import UniqueConstraint
from django.db.models import Q, Max
import random
import string


# Create your models here.
class UserManager(BaseUserManager):
    """
    Manager for User Model
    """

    def create_user(self, username, email, password, **extra_fields):
        """
        Create and return a new Useer without privileges
        """
        if not email:
            raise ValueError("User must have an email address")
        user = self.model(
            email=self.normalize_email(email), username=username, **extra_fields
        )
        user.set_password(password)
        user.save(using=self.db)
        return user

    def create_superuser(self, username, email, password):
        """
        Create and return a superuser
        """
        user = self.create_user(username, email, password)
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
    is_active = models.BooleanField(default=True)  # TODO: switch to email activation
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = "email"

    REQUIRED_FIELDS = [
        "username",
    ]

    def gen_rand_name(self):
        chars = string.ascii_letters
        rand_name = "".join(random.choice(chars) for x in range(4))
        return rand_name

    @property
    def create_username(self):
        username = self.first_name + self.gen_rand_name()
        self.username = username

    def save(self, *args, **kwargs):
        if self.username is None:
            self.create_username
        super(User, self).save(*args, **kwargs)


class Journal(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    journal_name = models.CharField(
        default="Untitled", max_length=200, null=True, blank=True
    )
    journal_description = models.CharField(max_length=3000, blank=True, null=True)
    current_table = models.IntegerField(null=True, blank=True)

    def __str__(self) -> str:
        return self.journal_name


def create_default_table_name():
    journal_tables = JournalTables.objects.filter(
        table_name__startswith="Table"
    ).values_list("table_name", flat=True)

    if len(journal_tables) == 0:
        return "Table"
    table_name = f"Table ({len(journal_tables)})"
    if table_name in journal_tables:
        return f"Table ({len(journal_tables) + 1})"
    else:
        return table_name


class JournalTables(models.Model):
    journal = models.ForeignKey(
        Journal, on_delete=models.CASCADE, related_name="journal_tables"
    )
    table_name = models.CharField(
        default=create_default_table_name, null=True, blank=True, max_length=100
    )

    def __str__(self) -> str:
        return self.table_name

    class Meta:
        ordering = ["id"]


class Activities(models.Model):
    name = models.CharField(max_length=3000, null=True, blank=True)
    created = models.DateTimeField(auto_now=True)
    journal_table = models.ForeignKey(
        JournalTables,
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="activities",
    )
    ordering = models.IntegerField(null=True, blank=True)

    @property
    def increment_ordering(self):
        journal_table_activities = Activities.objects.filter(
            journal_table=self.journal_table
        )
        journal_table_activities_count = journal_table_activities.count()
        if journal_table_activities_count == 0:
            self.ordering = 1
            # self.save()
        elif journal_table_activities_count > 0:
            highest_ordering = journal_table_activities.aggregate(Max("ordering"))
            self.ordering = highest_ordering["ordering__max"] + 1
            # self.save()

    def save(self, *args, **kwargs):
        if self.ordering is None:
            self.increment_ordering
        super(Activities, self).save(*args, **kwargs)

    def __str__(self) -> str:
        return self.name

    class Meta:
        ordering = ["ordering"]


class Tags(models.Model):
    class Colors(models.TextChoices):
        GRAY = (
            "Off Gray",
            "OFF GRAY",
        )
        GREEN = "Midnight Green", "MIDNIGHT GREEN"
        RED = "Wine Red", "WINE RED"
        ARMY_GREEN = "Army Green", "ARMY GREEN"
        YELLOW = "Yellow", "YELLOW"
        BLUE = "Light Blue", "LIGHT BLUE"
        PEACH = "Peach", "PEACH"
        TEAL = "Teal", "TEAL"
        PURPLE = "Deep Purple", "DEEP PURPLE"
        BROWN = "Brown", "BROWN"

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
    activities = models.ManyToManyField(Activities, related_name="tags", blank=True)

    class Meta:
        constraints = (
            UniqueConstraint(
                fields=["tag_user", "tag_name"],
                name="unique_tag_name",
            ),
        )

    def __str__(self) -> str:
        return self.tag_name


class BaseSubModel(models.Model):
    """
    Should be subclassed by every submodels that have to define a common property
    """

    @property
    def increment_ordering(self):
        submodel_instances = self.__class__.objects.filter(activity=self.activity)
        submodel_instances_count = submodel_instances.count()
        if submodel_instances_count == 0:
            self.ordering = 1
            # self.save()
        elif submodel_instances_count > 0:
            highest_ordering = submodel_instances.aggregate(Max("ordering"))
            self.ordering = highest_ordering["ordering__max"] + 1
            # self.save()

    class Meta:
        abstract = True

    def save(self, *args, **kwargs):
        if self.ordering is None:
            self.increment_ordering
        super().save(*args, **kwargs)


class Intentions(BaseSubModel):
    # TODO: add ordering to submodels, and implement re-ordering
    intention = models.CharField(max_length=2000)
    activity = models.ForeignKey(
        Activities,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="intentions",
    )
    ordering = models.IntegerField(null=True, blank=True)

    def __str__(self) -> str:
        return self.intention

    class Meta:
        ordering = ["ordering"]  # ["id"]


class Happenings(BaseSubModel):
    happening = models.CharField(max_length=2000)
    activity = models.ForeignKey(
        Activities,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="happenings",
    )
    ordering = models.IntegerField(null=True, blank=True)

    def __str__(self) -> str:
        return self.happening

    class Meta:
        ordering = ["ordering"]  # ["id"]


class GratefulFor(BaseSubModel):
    grateful_for = models.CharField(max_length=2000)
    activity = models.ForeignKey(
        Activities,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="grateful_for",
    )
    ordering = models.IntegerField(null=True, blank=True)

    def __str__(self) -> str:
        return self.grateful_for

    class Meta:
        ordering = ["ordering"]  # ["id"]


class ActionItems(BaseSubModel):
    action_item = models.CharField(max_length=2000)
    checked = models.BooleanField(default=False)
    activity = models.ForeignKey(
        Activities,
        null=True,
        blank=True,
        on_delete=models.CASCADE,
        related_name="action_items",
    )
    ordering = models.IntegerField(null=True, blank=True)

    def __str__(self) -> str:
        return self.action_item

    class Meta:
        ordering = ["ordering"]  # ["id"]
