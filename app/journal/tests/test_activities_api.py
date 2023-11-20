"""
Test for the Activities API
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse, resolve
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone
from datetime import datetime, timedelta
from core.models import Journal, Tags, Activities, JournalTables
from journal.serializers import ActivitiesSerializer
from django.db.models import Q

ACTIVITIES_URL = reverse("journal:activities-list")
CREATE_JOURNAL_TABLE_URL = reverse("journal:journaltables-list")
TOKEN_URL = reverse("user:token")


def detail_url(activies_id):
    """
    Returns the url for a tag detail
    """
    return reverse("journal:activities-detail", args=[activies_id])


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


class PublicActivitiesApiTests(TestCase):
    """
    Public activities api test
    """

    def setUp(self) -> None:
        self.client = APIClient()
        self.user_payload = {
            "first_name": "Test",
            "last_name": "User",
            "email": "user@example.com",
            "username": "testuser",
            "password": "Awesomeuser123",
        }

        self.user = create_user(**self.user_payload)
        self.user.is_active = True

    def test_activities_is_not_created_for_unauthenticated_user(self):
        """
        Test activities is not created for unauthenticated user
        """
        journal = Journal.objects.create(
            user=self.user,
            journal_name="Untitled",
            journal_description="klsdjs djdlf jsd jfldj sfjsdlf jladj faldsf adfdf",
        )

        journal_table = JournalTables.objects.create(
            table_name="New Table", journal=journal
        )

        tag1 = Tags.objects.create(
            tag_name="Daily",
            tag_user=self.user,
            tag_color=Tags.Colors.RED,
            tag_class=Tags.ColorsClasses.RED_CLASS,
        )
        tag2 = Tags.objects.create(
            tag_name="Work",
            tag_user=self.user,
            tag_color=Tags.Colors.GRAY,
            tag_class=Tags.ColorsClasses.GRAY_CLASS,
        )

        payload = {
            "name": "ldskjfafd",
            "journal_table": journal_table.id,
        }

        res = self.client.post(ACTIVITIES_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateActivitiesApiTests(TestCase):
    """
    Private activies api tests
    """

    def setUp(self) -> None:
        self.client = APIClient()
        self.user_payload = {
            "first_name": "Test",
            "last_name": "User",
            "email": "user@example.com",
            "username": "testuser",
            "password": "Awesomeuser123",
        }

        self.user = create_user(**self.user_payload)
        self.user.is_active = True

        self.tag1 = Tags.objects.create(
            tag_name="Daily",
            tag_user=self.user,
            tag_color=Tags.Colors.RED,
            tag_class=Tags.ColorsClasses.RED_CLASS,
        )
        self.tag2 = Tags.objects.create(
            tag_name="Work",
            tag_user=self.user,
            tag_color=Tags.Colors.GRAY,
            tag_class=Tags.ColorsClasses.GRAY_CLASS,
        )

        self.journal = Journal.objects.create(
            user=self.user,
            journal_name="Untitled",
            journal_description="klsdjs djdlf jsd jfldj sfjsdlf jladj faldsf adfdf",
        )
        self.client.force_authenticate(self.user)

    def test_create_activities_for_authenticated_user_is_successful(self):
        """
        Test create activities for authenticated user is successful
        """

        journal_table = JournalTables.objects.create(
            table_name="New Table", journal=self.journal
        )

        payload = {
            "name": "ldskjfafd",
            "journal_table": journal_table.id,
            "tags": [self.tag1.id, self.tag2.id],  # values(),  # values(),
        }

        res = self.client.post(ACTIVITIES_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        activity = Activities.objects.filter(journal_table=journal_table)

        serializer = ActivitiesSerializer(activity, many=True)
        self.assertQuerySetEqual(serializer.data[0]["tags"], res.data["tags"])

    def test_remove_activites_for_other_user_by_current_user_fails(self):
        """
        Test that a current user cannot remove activities for another user
        """
        journal_table = JournalTables.objects.create(
            table_name="New Table", journal=self.journal
        )

        user_payload = {
            "first_name": "Test",
            "last_name": "User",
            "email": "user2@example.com",
            "username": "testuser",
            "password": "Awesomeuser123",
        }

        user = create_user(**user_payload)

        activities = Activities.objects.create(
            name="Kdf sfsdf",
            journal_table=journal_table,
        )
        activities.tags.add(self.tag1)
        activities.tags.add(self.tag2)

        self.client.force_authenticate(user)
        activities_url = detail_url(activities.id)
        res = self.client.delete(activities_url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_remove_activities_by_created_user_is_successful(self):
        """
        Test remove activities by created user is successful
        """

        journal_table = JournalTables.objects.create(
            table_name="New Table", journal=self.journal
        )

        activities = Activities.objects.create(
            name="Kdf sfsdf",
            journal_table=journal_table,
        )
        activities.tags.add(self.tag1)
        activities.tags.add(self.tag2)
        activities_url = detail_url(activities.id)
        res = self.client.delete(activities_url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        activities_count = Activities.objects.filter(
            journal_table=journal_table
        ).count()
        self.assertEqual(activities_count, 0)

    def test_full_update_an_activities(self):
        """
        Test a put request update on a created activities
        """
        journal_table = JournalTables.objects.create(
            table_name="New Table", journal=self.journal
        )

        activities = Activities.objects.create(
            name="Kdf sfsdf",
            journal_table=journal_table,
        )
        activities.tags.add(self.tag1)
        activities.tags.add(self.tag2)

        self.client.force_authenticate(self.user)

        activities_url = detail_url(activities.id)
        payload = {
            "name": "kdv ef",
            "tags": [self.tag1.id],
        }
        res = self.client.put(activities_url, payload)
        activities.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(payload["name"], activities.name)

    def test_partial_update_of_an_activity(self):
        """
        Test a patch update of an activity
        """
        journal_table = JournalTables.objects.create(
            table_name="New Table", journal=self.journal
        )

        activities = Activities.objects.create(
            name="Kdf sfsdf",
            journal_table=journal_table,
        )
        activities.tags.add(self.tag1)
        activities.tags.add(self.tag2)

        self.client.force_authenticate(self.user)

        activities_url = detail_url(activities.id)
        payload = {"name": "kdv ef"}
        res = self.client.patch(activities_url, payload)
        activities.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(payload["name"], activities.name)
