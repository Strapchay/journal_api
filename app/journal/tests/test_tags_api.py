"""
Test for the Tags API
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse, resolve
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone
from datetime import datetime, timedelta
from core.models import Journal, Tags
from django.db.models import Q

TAGS_URL = reverse("journal:tags-list")
# CREATE_J_URL = reverse("journal:journaltables-list")
TOKEN_URL = reverse("user:token")


def detail_url(tag_id):
    """
    Returns the url for a tag detail
    """
    return reverse("journal:tag-detail", args=[tag_id])


def create_user(**params):
    """
    Create and return a user
    """
    return get_user_model().objects.create_user(**params)


def create_journal(
    user,
    journal_name="new journal",
    journal_description="kvldsjfksd sdjflsjd lfjsldjf jdlfjd sfsdff",
):
    """
    Create and return a journal
    """
    return Journal.objects.create(
        journal_name=journal_name, journal_description=journal_description, user=user
    )


class PublicTagsApiTest(TestCase):
    """
    Public tests for the tags api
    """

    def setUp(self) -> None:
        self.client = APIClient()
        self.payload = {
            "tag_name": "Daily",
            "tag_color": Tags.Colors.RED,
            "tag_class": Tags.ColorsClasses.RED_CLASS,
        }

    def test_create_tag_for_unauthenticated_user(self):
        """
        Test that creating a tag for an unauthenticated user fails
        """

        res = self.client.post(TAGS_URL, self.payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateTagsApiTest(TestCase):
    """
    Private tests for the tags api
    """

    def setUp(self):
        self.client = APIClient()
        user_payload = {
            "first_name": "Test",
            "last_name": "User",
            "email": "user@example.com",
            "password": "Awesomeuser123",
        }
        self.user = create_user(**user_payload)
        # self.journal = create_journal(self.user)

        self.client.force_authenticate(self.user)

    def test_create_tag_for_authenticated_user(self):
        """
        Test creating  tag for an authenticated user is successful
        """
        payload = {
            "tag_user": self.user.id,
            "tag_name": "Daily",
            "tag_color": Tags.Colors.RED,
            "tag_class": Tags.ColorsClasses.RED_CLASS,
        }

        res = self.client.post(TAGS_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_create_tag_for_authenticated_user_with_tag_color_not_in_choices_fails(
        self,
    ):
        """
        Test creating a tag for authenticated users with the tag color and tag_class not in the choices fields fails
        """
        payload = {
            "tag_user": self.user.id,
            "tag_name": "Daily",
            "tag_color": "dsklfjasdf",
            "tag_class": "ldsjfaldfads",
        }
        res = self.client.post(TAGS_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_creating_tag_with_same_tag_name_fails(self):
        """
        Test creating a tag with th same tag name fails
        """
        payload = {
            "tag_user": self.user.id,
            "tag_name": "Daily",
            "tag_color": Tags.Colors.RED,
            "tag_class": Tags.ColorsClasses.RED_CLASS,
        }

        res = self.client.post(TAGS_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        res2 = self.client.post(TAGS_URL, payload)
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_superuser_tags_is_returned_for_normal_user(self):
        """
        Test that tags created by superusers are returned for normal users
        """
        self.user.is_superuser = True
        self.user.save()

        payload = {
            "tag_user": self.user.id,
            "tag_name": "Daily",
            "tag_color": Tags.Colors.RED,
            "tag_class": Tags.ColorsClasses.RED_CLASS,
        }

        res = self.client.post(TAGS_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        user_payload = {
            "first_name": "Test",
            "last_name": "User",
            "email": "testuser@example.com",
            "password": "Awesomeuser123",
        }
        user = create_user(**user_payload)

        payload = {
            "tag_user": user.id,
            "tag_name": "daily",
            "tag_color": Tags.Colors.RED,
            "tag_class": Tags.ColorsClasses.RED_CLASS,
        }

        res2 = self.client.post(TAGS_URL, payload)

        tags = Tags.objects.filter(
            Q(tag_user=user) | Q(tag_user__is_superuser=True)
        ).values_list("tag_name", flat=True)

        formatted_tag_name = (
            payload["tag_name"][0].upper() + payload["tag_name"][1:].lower()
        )

        self.assertIn(formatted_tag_name, tags)
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_created_tag_name_is_capitalized(self):
        """
        Test that the created tag_name value is capitalized if supplied in lower or uppercase
        """
        user_payload = {
            "first_name": "Test",
            "last_name": "User",
            "email": "testuser@example.com",
            "password": "Awesomeuser123",
        }
        user = create_user(**user_payload)

        payload = {
            "tag_user": user.id,
            "tag_name": "daily",
            "tag_color": Tags.Colors.RED,
            "tag_class": Tags.ColorsClasses.RED_CLASS,
        }

        res = self.client.post(TAGS_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertTrue(res.data["tag_name"], "Daily")

    # def test_user
