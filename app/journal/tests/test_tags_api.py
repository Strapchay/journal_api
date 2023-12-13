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
BATCH_TAG_URL = reverse("journal:tags-batch_tag_processor")
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
            "username": "testuser",
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

    def test_create_batch_tags_is_successful(self):
        """
        Test creating batch tags for an authenticated user is successful
        """
        payload = {
            "tags_list": [
                {
                    "tag_name": "Daily",
                    "tag_color": Tags.Colors.RED,
                    "tag_class": Tags.ColorsClasses.RED_CLASS,
                },
                {
                    "tag_name": "Kdoifaf",
                    "tag_color": Tags.Colors.GRAY,
                    "tag_class": Tags.ColorsClasses.GRAY_CLASS,
                },
                {
                    "tag_name": "Kiovodaf",
                    "tag_color": Tags.Colors.BLUE,
                    "tag_class": Tags.ColorsClasses.BLUE_CLASS,
                },
            ]
        }

        res = self.client.post(BATCH_TAG_URL, payload, format="json")
        print("btach tag createe", res.data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        tags_count = Tags.objects.filter(tag_user=self.user.id).count()
        self.assertEqual(tags_count, 3)

    def test_create_batch_tags_with_a_invalid_data_is_successful(self):
        """
        Test creating batch tags with one of its value being invalid still result in a success
        """

        payload = {
            "tags_list": [
                {
                    "tag_name": "Daily",
                    "tag_color": Tags.Colors.RED,
                    "tag_class": Tags.ColorsClasses.RED_CLASS,
                },
                {
                    "tag_name": None,
                    "tag_color": None,
                    "tag_class": Tags.ColorsClasses.GRAY_CLASS,
                },
                {
                    "tag_name": "Kiovodaf",
                    "tag_color": Tags.Colors.BLUE,
                    "tag_class": Tags.ColorsClasses.BLUE_CLASS,
                },
            ]
        }

        res = self.client.post(BATCH_TAG_URL, payload, format="json")
        print("btach tag createe inval data", res.data)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        tags_count = Tags.objects.filter(tag_user=self.user.id).count()
        self.assertEqual(tags_count, 2)

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

    def test_creating_a_tag_with_not_matching_tag_color_and_class_fails(self):
        """
        Test creating a tag with tag_color and tag_class not matching or relative to each other fails
        """
        payload = {
            "tag_user": self.user.id,
            "tag_name": "Daily",
            "tag_color": Tags.Colors.RED,
            "tag_class": Tags.ColorsClasses.GRAY_CLASS,
        }

        res = self.client.post(TAGS_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

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
            "username": "testuser",
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
            "username": "testuser",
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

    def test_updating_batch_tags_is_successful(self):
        """
        Test updating batch tags with one of its value being invalid still result in a success
        """
        tag1_payload = {
            "tag_user": self.user,
            "tag_name": "Daily",
            "tag_color": Tags.Colors.RED,
            "tag_class": Tags.ColorsClasses.RED_CLASS,
        }

        tag2_payload = {
            "tag_user": self.user,
            "tag_name": "adsadsf",
            "tag_color": Tags.Colors.GRAY,
            "tag_class": Tags.ColorsClasses.GRAY_CLASS,
        }

        tag3_payload = {
            "tag_user": self.user,
            "tag_name": "Kiovodaf",
            "tag_color": Tags.Colors.BLUE,
            "tag_class": Tags.ColorsClasses.BLUE_CLASS,
        }

        tag1 = Tags.objects.create(**tag1_payload)
        tag2 = Tags.objects.create(**tag2_payload)
        tag3 = Tags.objects.create(**tag3_payload)

        payload = {
            "tags_list": [
                {
                    "id": tag1.id,
                    "tag_name": "Dai",
                    "tag_color": Tags.Colors.BLUE,
                    "tag_class": Tags.ColorsClasses.BLUE_CLASS,
                },
                {
                    "id": tag2.id,
                    "tag_name": "Updated Name",
                    "tag_color": Tags.Colors.RED,
                    "tag_class": Tags.ColorsClasses.RED_CLASS,
                },
                {
                    "id": tag3.id,
                    "tag_name": "Kiovodaf",
                    "tag_color": Tags.Colors.YELLOW,
                    "tag_class": Tags.ColorsClasses.YELLOW_CLASS,
                },
            ]
        }

        res = self.client.patch(BATCH_TAG_URL, payload, format="json")
        print("btach tag createe inval data", res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        tag1.refresh_from_db()
        tag2.refresh_from_db()
        self.assertEqual(tag1.tag_name, payload["tags_list"][0]["tag_name"])
        self.assertEqual(tag2.tag_color, payload["tags_list"][1]["tag_color"])

    def test_deleting_batch_tags_is_successful(self):
        """
        Test deleting batch tags is successful
        """
        tag1_payload = {
            "tag_user": self.user,
            "tag_name": "Daily",
            "tag_color": Tags.Colors.RED,
            "tag_class": Tags.ColorsClasses.RED_CLASS,
        }

        tag2_payload = {
            "tag_user": self.user,
            "tag_name": "adsadsf",
            "tag_color": Tags.Colors.GRAY,
            "tag_class": Tags.ColorsClasses.GRAY_CLASS,
        }

        tag3_payload = {
            "tag_user": self.user,
            "tag_name": "Kiovodaf",
            "tag_color": Tags.Colors.BLUE,
            "tag_class": Tags.ColorsClasses.BLUE_CLASS,
        }

        tag1 = Tags.objects.create(**tag1_payload)
        tag2 = Tags.objects.create(**tag2_payload)
        tag3 = Tags.objects.create(**tag3_payload)

        payload = {"tags_list": [tag3.id, tag1.id]}

        res = self.client.delete(BATCH_TAG_URL, payload, format="json")
        print("btach tag createe inval data", res.data)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        tags_count = Tags.objects.filter(tag_user=self.user).count()

        self.assertEqual(tags_count, 1)

    def test_deleting_batch_tags_with_invalid_id_is_successful(self):
        """
        Test deleting batch tags with one of its tag id non-existent is successful and doesn't invalidate the request
        """
        tag1_payload = {
            "tag_user": self.user,
            "tag_name": "Daily",
            "tag_color": Tags.Colors.RED,
            "tag_class": Tags.ColorsClasses.RED_CLASS,
        }

        tag2_payload = {
            "tag_user": self.user,
            "tag_name": "adsadsf",
            "tag_color": Tags.Colors.GRAY,
            "tag_class": Tags.ColorsClasses.GRAY_CLASS,
        }

        tag3_payload = {
            "tag_user": self.user,
            "tag_name": "Kiovodaf",
            "tag_color": Tags.Colors.BLUE,
            "tag_class": Tags.ColorsClasses.BLUE_CLASS,
        }

        tag1 = Tags.objects.create(**tag1_payload)
        tag2 = Tags.objects.create(**tag2_payload)
        tag3 = Tags.objects.create(**tag3_payload)

        payload = {"tags_list": [tag3.id, tag1.id, 84398434]}

        res = self.client.delete(BATCH_TAG_URL, payload, format="json")
        print("btach tag createe inval data", res.data)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        tags_count = Tags.objects.filter(tag_user=self.user).count()

        self.assertEqual(tags_count, 1)
