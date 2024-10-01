"""
Test for the Journal API
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone
from datetime import datetime, timedelta
from core.models import Journal, JournalTables, Tags
from journal.serializers import JournalSerializer

CREATE_JOURNAL_URL = reverse("journal:journal-list")
TOKEN_URL = reverse("user:token")

# ME_URL = reverse("user:me")


def detail_url(journal_id):
    """
    Returns the url for a journal detail
    """
    return reverse("journal:journal-detail", args=[journal_id])


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


class PublicJournalApiTests(TestCase):
    """
    Test the public features of the journal API
    """

    def setUp(self):
        self.client = APIClient()
        self.payload = {
            "first_name": "Test",
            "last_name": "User",
            "email": "user@example.com",
            "username": "testuser",
            "password": "Awesomeuser123",
        }
        self.user = create_user(**self.payload)
        # self.client.force_authenticate(self.user)

    def test_create_journal_unauthenticated_fails(self):
        """
        Test creating a journal by an unauthenticated user fails
        """

        # user = create_user(**user_payload)

        payload = {
            "user": self.user.id,
            "journal_name": "lkdjfsldjfd dfjs",
            "journal_description": "kdlsfjsldkjf sldjflsdkjf lskdjflsdj fljsdlk fjlsdj fljsdlfkjdfljdf",
        }
        # user_journal = create_journal()
        res = self.client.post(CREATE_JOURNAL_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateJournalApiTests(TestCase):
    """
    Private Tests for Journal Api
    """

    def setUp(self):
        self.user_payload = {
            "first_name": "Test",
            "last_name": "User",
            "email": "user@example.com",
            "username": "testuser",
            "password": "Awesomeuser123",
        }

        self.user = create_user(**self.user_payload)
        self.user.is_active = True

        self.client = APIClient()
        self.client.force_authenticate(self.user)

        self.payload = {
            "user": self.user,
            "journal_name": "vkldjflsdj fdlksjdfd",
            "journal_description": "klvjlsdkjfd sdjflasdjfs jsdk fjsd fjlsjdf ljdjf lj fjsd f",
        }

    def test_journal_is_created_successfully(self):
        """
        Test that creating a journal is successful
        """
        self.payload["user"] = self.user.id
        res = self.client.post(CREATE_JOURNAL_URL, self.payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

    def test_journal_is_created_successfully_and_creates_default_tables(self):
        """
        Test that creating a journal also creates the default tables for it
        """
        self.payload["user"] = self.user.id
        res = self.client.post(CREATE_JOURNAL_URL, self.payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        created_journal = Journal.objects.get(id=res.data["id"])
        serializer = JournalSerializer(created_journal)
        journal_tables_count = JournalTables.objects.filter(
            journal__id=res.data["id"]
        ).count()
        self.assertEqual(journal_tables_count, 3)
        self.assertEqual(res.data, serializer.data)

    def test_journal_is_created_successfully_and_sets_the_default_current_table(self):
        """
        Test that creating a journal also sets a default currenttable
        """
        self.payload["user"] = self.user.id
        res = self.client.post(CREATE_JOURNAL_URL, self.payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        created_journal = Journal.objects.get(id=res.data["id"])
        journal_table_first = JournalTables.objects.filter(
            journal__id=res.data["id"]
        ).first()
        self.assertEqual(journal_table_first.id, created_journal.current_table)

    def test_admin_tags_copied_for_journal_user(self):
        """
        Tests that the admin default created tags were copied for the journal user
        """
        self.user.is_superuser = True
        self.user.save()

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

        user_payload = self.user_payload.copy()
        user_payload["email"] = "user2@example.com"

        user = create_user(**user_payload)
        self.client.force_authenticate(user)

        self.payload["user"] = user.id

        res = self.client.post(CREATE_JOURNAL_URL, self.payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user_tags_count = Tags.objects.filter(tag_user=user).count()
        self.assertEqual(user_tags_count, 2)

    def test_journal_full_update(self):
        """
        Test that updating a journal with a put is successful
        """

        payload = {
            "journal_name": "Untitled Journal",
            "journal_description": "lsdkjflsadjfl dfjklsjdlfkjsdff",
        }

        journal = create_journal(**self.payload)
        journal_url = detail_url(journal.id)
        res = self.client.put(journal_url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_journal_partial_update_is_successful(self):
        """
        Test that updating a journal with a patch is successful
        """
        journal = create_journal(**self.payload)
        journal_url = detail_url(journal.id)
        payload = {"journal_name": "Untitled"}
        res = self.client.patch(journal_url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        journal.refresh_from_db()
        self.assertEqual(payload["journal_name"], journal.journal_name)

    def test_journal_partial_update_of_current_table_sets_a_default(self):
        """
        Test that updating a journals current_table sets a default table if the table to be set as current_table does not exist
        """
        self.payload["user"] = self.user.id
        res = self.client.post(CREATE_JOURNAL_URL, self.payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        created_journal = Journal.objects.get(id=res.data["id"])
        journal_table = JournalTables.objects.filter(journal__id=res.data["id"])
        journal_table.first().delete()
        journal_table_first = journal_table.first().id

        journal_url = detail_url(res.data["id"])
        payload = {"journal_name": "Untitled", "current_table": 83923}

        res = self.client.patch(journal_url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["current_table"], journal_table_first)

    def test_journal_partial_update_of_current_table_is_successful(self):
        """
        Test that updating a journals current_table updates to the specified value
        """
        self.payload["user"] = self.user.id
        res = self.client.post(CREATE_JOURNAL_URL, self.payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        created_journal = Journal.objects.get(id=res.data["id"])
        journal_table = JournalTables.objects.filter(journal__id=res.data["id"])
        journal_table_last = journal_table.last().id

        journal_url = detail_url(res.data["id"])
        payload = {"journal_name": "Untitled", "current_table": journal_table_last}

        res = self.client.patch(journal_url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["current_table"], journal_table_last)

    def test_journal_partial_update_of_current_table_table_func(self):
        """
        Test that updating a journals current_table table_func json is saved and queriable
        """

        journal = Journal.objects.create(**self.payload)

        table_func_data = {
            "journal_table_func": {
                "15": {
                    "filter": {
                        "tableId": 15,
                        "type": "itemTitle",
                        "conditional": "ends with",
                        "value": "ff",
                        "property": "name",
                    },
                    "sort": {},
                }
            }
        }
        journal_url = detail_url(journal.id)
        res = self.client.patch(journal_url, table_func_data, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)


        self.assertEqual(
            res.data["journal_table_func"], table_func_data["journal_table_func"]
        )

    def test_journal_partial_update_of_current_table_cannot_set_default_if_none_exists(
        self,
    ):
        """
        Test that updating a journals current_table sets a default table if the table to be set as current_table does not exist
        """
        self.payload["user"] = self.user.id
        res = self.client.post(CREATE_JOURNAL_URL, self.payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        created_journal = Journal.objects.get(id=res.data["id"])
        journal_table = JournalTables.objects.filter(journal__id=res.data["id"])
        journal_table.delete()

        journal_url = detail_url(res.data["id"])
        payload = {"journal_name": "Untitled", "current_table": 83923}

        res = self.client.patch(journal_url, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertEqual(res.data["current_table"], None)

    def test_retrieve_journal_for_user(self):
        """
        Test retrieving journal for user
        """
        journal = create_journal(**self.payload)
        res = self.client.get(CREATE_JOURNAL_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        journal.refresh_from_db()
        self.assertEqual(res.data[0]["journal_name"], journal.journal_name)

    def test_retrieve_journal_for_user_returns_linked_journal_tables(self):
        """
        Test retrieving created journal returns journal tables linked to it
        """
        journal = create_journal(**self.payload)
        journal_table_payload = {"journal": journal, "table_name": "journal table"}
        journal_table1 = JournalTables.objects.create(**journal_table_payload)
        journal_table2 = JournalTables.objects.create(**journal_table_payload)

        res = self.client.get(CREATE_JOURNAL_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        updated_journal = Journal.objects.filter(id=journal.id)
        serializer = JournalSerializer(updated_journal, many=True)
        self.assertEqual(res.data, serializer.data)

    def test_retrieve_journal_for_user_returns_user_tags(self):
        """
        Tests that the admin default created tags were copied for the journal user
        """
        self.user.is_superuser = True
        self.user.save()

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

        user_payload = self.user_payload.copy()
        user_payload["email"] = "user2@example.com"

        user = create_user(**user_payload)
        self.client.force_authenticate(user)

        self.payload["user"] = user.id

        res = self.client.post(CREATE_JOURNAL_URL, self.payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user_tags_count = Tags.objects.filter(tag_user=user).count()
        self.assertEqual(user_tags_count, 2)

        # retrieve journal
        url = detail_url(res.data["id"])
        res = self.client.get(url)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("tags", res.data)
