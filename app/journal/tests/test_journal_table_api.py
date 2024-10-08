"""
Test for the Journal Table API
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse, resolve
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone
from datetime import datetime, timedelta
from core.models import (
    Journal,
    JournalTables,
    ActionItems,
    Activities,
    Intentions,
    Happenings,
    GratefulFor,
    Tags,
)

CREATE_JOURNAL_URL = reverse("journal:journal-list")
CREATE_JOURNAL_TABLE_URL = reverse("journal:journaltables-list")
TOKEN_URL = reverse("user:token")


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


def detail_url(journal_table_id):
    """
    Return the url for a journal table
    """
    return reverse("journal:journaltables-detail", args=[journal_table_id])


class PublicJournalTableApiTest(TestCase):
    """
    Test the public features for the journal table api
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
        self.journal = create_journal(self.user)

        # self.client.force_authenticate(self.user)

    def test_create_journal_table_for_unauthenticated_user(self):
        """
        Test creating journal table for unauthenticated users fails
        """
        payload = {
            "journal": self.journal.id,
            "table_name": "skdvn djfsldkjfsdf",
        }
        res = self.client.post(CREATE_JOURNAL_TABLE_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_retrieve_journal_table_for_unauthenticated_user(self):
        """
        Test retrieving journal table for unauthenticated users fails
        """
        res = self.client.get(CREATE_JOURNAL_TABLE_URL)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateJournalTableApiTests(TestCase):
    """
    Private tests for journal table api
    """

    def setUp(self) -> None:
        self.client = APIClient()
        user_payload = {
            "first_name": "Test",
            "last_name": "User",
            "email": "user@example.com",
            "username": "testuser",
            "password": "Awesomeuser123",
        }
        self.user = create_user(**user_payload)
        self.journal = create_journal(self.user)

        self.client.force_authenticate(self.user)

    def test_create_journal_table_succeeds(self):
        """
        Test create journal table succeeds for
        authenticated user
        """
        payload = {"journal": self.journal.id, "table_name": "kdljfaklsd jfsdf"}

        res = self.client.post(CREATE_JOURNAL_TABLE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_create_journal_table_as_duplicate_succeeds(self):
        """
        Test create journal table by duplicating a journal table succeeds for
        authenticated user
        """
        journal_table = JournalTables.objects.create(
            journal=self.journal, table_name="Table"
        )

        payload = {
            "journal": self.journal.id,
            "journal_table": journal_table.id,
            "duplicate": True,
            "table_name": "",
        }
        res = self.client.post(CREATE_JOURNAL_TABLE_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(res.data["table_name"], f"{journal_table.table_name} (1)")

    def test_create_journal_table_without_table_name_creates_default_table_name(self):
        """
        Test create journal table without table_name creates default table with table name
        """
        journal_table = JournalTables.objects.create(journal=self.journal)

        payload = {
            "journal": self.journal.id,
        }
        res = self.client.post(CREATE_JOURNAL_TABLE_URL, payload, format="json")

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        self.assertEqual(journal_table.table_name, "Table")
        self.assertEqual(res.data["table_name"], f"Table (1)")

    def test_retrieving_journal_table_activities_with_sub_fields_are_returned_in_response(
        self,
    ):
        """
        Test retrieving activities with sub_fields are returned in the serialized response
        """
        journal_table = JournalTables.objects.create(
            table_name="New Table", journal=self.journal
        )

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

        activity = Activities.objects.create(
            name="kldjfsd jdfldsjfd jddfsasf", journal_table=journal_table
        )
        activity.tags.add(self.tag1)
        activity.tags.add(self.tag2)

        intentions = Intentions.objects.create(
            activity=activity, intention="dkjvlsdj fdjsfkajdf djfdfa"
        )
        happenings = Happenings.objects.create(
            activity=activity, happening="kdlv dfjadjldf fjdsadffd"
        )
        grateful_for = GratefulFor.objects.create(
            activity=activity, grateful_for="kdljvsdj dfjdsjadf"
        )
        action_items = ActionItems.objects.create(
            activity=activity, action_item="kdslj dfdjadfj fdjfadjffd"
        )
        url = detail_url(journal_table.id)
        res = self.client.get(url)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("activities", res.data)

    def test_retrieve_journal_table_succeeds(self):
        """
        Test retrieve journal table succeeds for authenticated user
        """
        payload = {"journal": self.journal.id, "table_name": "kdljfaklsd jfsdf"}

        res = self.client.post(CREATE_JOURNAL_TABLE_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        res2 = self.client.get(CREATE_JOURNAL_TABLE_URL)
        self.assertEqual(res2.status_code, status.HTTP_200_OK)

    def test_delete_journal_table_succeeds(self):
        """
        Test delete journal table succeeds for authenticated user
        """
        journal_table = JournalTables.objects.create(
            journal=self.journal, table_name="lsdfjsdf dskfjlsdfjdsff"
        )

        JournalTables.objects.create(journal=self.journal, table_name="lsdfjsdf")

        delete_url = detail_url(journal_table.id)

        res = self.client.delete(delete_url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        journal_tables = JournalTables.objects.filter(journal=self.journal)
        self.assertEqual(journal_tables.count(), 1)

    def test_delete_journal_current_journal_table_updates_journal_current_table(self):
        """
        Test delete journal table which is the journal's current table updates the journal current table
        """
        journal_table = JournalTables.objects.create(
            journal=self.journal, table_name="lsdfjsdf dskfjlsdfjdsff"
        )

        journal_table2 = JournalTables.objects.create(
            journal=self.journal, table_name="l;kjdslkjfad"
        )

        journal_table3 = JournalTables.objects.create(
            journal=self.journal, table_name="skdjfdsf"
        )

        self.journal.current_table = journal_table.id
        self.journal.save()

        delete_url = detail_url(journal_table.id)

        res = self.client.delete(delete_url)
        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        self.journal.refresh_from_db()
        journal_tables = JournalTables.objects.filter(journal=self.journal)
        self.assertEqual(journal_tables.count(), 2)

        self.assertEqual(self.journal.current_table, journal_table2.id)

    def test_delete_only_journal_table_fails(self):
        """
        Test delete the only journal table fails for authenticated user
        """
        journal_table = JournalTables.objects.create(
            journal=self.journal, table_name="lsdfjsdf dskfjlsdfjdsff"
        )

        delete_url = detail_url(journal_table.id)

        res = self.client.delete(delete_url)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)
        journal_tables = JournalTables.objects.filter(journal=self.journal)
        self.assertEqual(journal_tables.count(), 1)

    def test_delete_journal_for_other_user_by_authenticated_user_fails(self):
        """
        Test deleting journal for other user by the authenticated user fails
        """
        journal_table = JournalTables.objects.create(
            journal=self.journal, table_name="lsdfjsdf dskfjlsdfjdsff"
        )

        user_payload = {
            "first_name": "Test",
            "last_name": "User",
            "email": "user2@example.com",
            "username": "testuser",
            "password": "Awesomeuser123",
        }
        user = create_user(**user_payload)
        self.client.force_authenticate(user)
        delete_url = detail_url(journal_table.id)

        res = self.client.delete(delete_url)
        self.assertEqual(res.status_code, status.HTTP_404_NOT_FOUND)

    def test_full_update_of_journal_table(self):
        """
        Test full update of a journal table succeeds
        """
        journal_table = JournalTables.objects.create(
            journal=self.journal, table_name="lsdfjsdf dskfjlsdfjdsff"
        )

        update_url = detail_url(journal_table.id)
        payload = {"table_name": "full update"}

        res = self.client.put(update_url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        journal_table.refresh_from_db()
        self.assertEqual(res.data["table_name"], payload["table_name"])

    def test_partial_update_of_journal_table(self):
        """
        Test partial update of a journal table succeeds
        """
        journal_table = JournalTables.objects.create(
            journal=self.journal, table_name="lsdfjsdf dskfjlsdfjdsff"
        )

        update_url = detail_url(journal_table.id)
        payload = {"table_name": "dklkfsdf"}

        res = self.client.patch(update_url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        journal_table.refresh_from_db()
        self.assertEqual(res.data["table_name"], payload["table_name"])
