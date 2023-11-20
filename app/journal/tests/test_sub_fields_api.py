"""
Test for the Happenings,Intentions and Grateful API
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone
from datetime import datetime, timedelta
from core.models import (
    Journal,
    JournalTables,
    Activities,
    Intentions,
    Happenings,
    ActionItems,
    GratefulFor,
)

INTENTIONS_URL = reverse("journal:intentions-list")
HAPPENINGS_URL = reverse("journal:happenings-list")
GRATEFUL_FOR_URL = reverse("journal:gratefulfor-list")
ACTION_ITEMS_URL = reverse("journal:actionitems-list")
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


def obj_detail_url(url_name, obj_id):
    """
    Return the detail url for the model resource
    """
    return reverse(f"journal:{url_name}-detail", args=[obj_id])


class PublicSubFieldsApiTests(TestCase):
    """
    Public tests for sub fields api
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

        self.journal = Journal.objects.create(
            user=self.user,
            journal_name="Untitled",
            journal_description="klsdjs djdlf jsd jfldj sfjsdlf jladj faldsf adfdf",
        )

        self.journal_table = JournalTables.objects.create(
            table_name="New Table", journal=self.journal
        )

    def test_intentions_create_for_unauthenticated_users(self):
        """
        Test the intentions cannot be created for unauthenticated users
        """
        activities = Activities.objects.create(
            name="ldskjfafd", journal_table=self.journal_table
        )

        payload = {
            "intention": "ldskfsd dfjlsdjfsdaf dfasdaffd",
            "activity": activities.id,
        }

        res = self.client.post(INTENTIONS_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_happenings_create_for_unauthenticated_users(self):
        """
        Test the happenings cannot be created for unauthenticated users
        """
        activities = Activities.objects.create(
            name="ldskjfafd", journal_table=self.journal_table
        )

        payload = {
            "happening": "ldskfsd dfjlsdjfsdaf dfasdaffd",
            "activity": activities.id,
        }

        res = self.client.post(HAPPENINGS_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_grateful_for_create_for_unauthenticated_users(self):
        """
        Test the grateful_for cannot be created for unauthenticated users
        """
        activities = Activities.objects.create(
            name="ldskjfafd", journal_table=self.journal_table
        )

        payload = {
            "grateful_for": "ldskfsd dfjlsdjfsdaf dfasdaffd",
            "activity": activities.id,
        }

        res = self.client.post(GRATEFUL_FOR_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_action_items_create_for_unauthenticated_users(self):
        """
        Test the action_items cannot be created for unauthenticated users
        """
        activities = Activities.objects.create(
            name="ldskjfafd", journal_table=self.journal_table
        )

        payload = {
            "action_item": "ldskfsd dfjlsdjfsdaf dfasdaffd",
            "activity": activities.id,
        }

        res = self.client.post(ACTION_ITEMS_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)


class PrivateIntentionsApiTests(TestCase):
    """
    Private tests for intentions api
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
        self.journal = Journal.objects.create(
            user=self.user,
            journal_name="Untitled",
            journal_description="klsdjs djdlf jsd jfldj sfjsdlf jladj faldsf adfdf",
        )
        self.journal_table = JournalTables.objects.create(
            table_name="New Table", journal=self.journal
        )
        self.client.force_authenticate(self.user)

    # create for sub fields
    def test_create_intentions_for_authenticated_users(self):
        """
        Test creating intentions for authenticated users is successful
        """
        activities = Activities.objects.create(
            name="ldskjfafd", journal_table=self.journal_table
        )
        payload = {
            "intention": "ldskfsd dfjlsdjfsdaf dfasdaffd",
            "activity": activities.id,
        }
        res = self.client.post(INTENTIONS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        intention = Intentions.objects.get(activity__id=activities.id)
        self.assertEqual(intention.intention, payload["intention"])

    def test_create_happenings_for_authenticated_users(self):
        """
        Test creating happenings for authenticated users is successful
        """
        activities = Activities.objects.create(
            name="ldskjfafd", journal_table=self.journal_table
        )
        payload = {
            "happening": "ldskfsd dfjlsdjfsdaf dfasdaffd",
            "activity": activities.id,
        }
        res = self.client.post(HAPPENINGS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        happening = Happenings.objects.get(activity__id=activities.id)
        self.assertEqual(happening.happening, payload["happening"])

    def test_create_grateful_for_for_authenticated_users(self):
        """
        Test creating grateful_for for authenticated users is successful
        """
        activities = Activities.objects.create(
            name="ldskjfafd", journal_table=self.journal_table
        )
        payload = {
            "grateful_for": "ldskfsd dfjlsdjfsdaf dfasdaffd",
            "activity": activities.id,
        }
        res = self.client.post(GRATEFUL_FOR_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        grateful_for = GratefulFor.objects.get(activity__id=activities.id)
        self.assertEqual(grateful_for.grateful_for, payload["grateful_for"])

    def test_create_action_items_for_authenticated_users(self):
        """
        Test creating action_items for authenticated users is successful
        """
        activities = Activities.objects.create(
            name="ldskjfafd", journal_table=self.journal_table
        )
        payload = {
            "action_item": "ldskfsd dfjlsdjfsdaf dfasdaffd",
            "activity": activities.id,
        }
        res = self.client.post(ACTION_ITEMS_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        action_item = ActionItems.objects.get(activity__id=activities.id)
        self.assertEqual(action_item.action_item, payload["action_item"])

    # retrieving tests for sub models
    def test_retrieving_intentions_is_successful(self):
        """
        Test retrieving intentions is successful
        """
        activities = Activities.objects.create(
            name="ldskjfafd", journal_table=self.journal_table
        )

        Intentions.objects.create(
            intention="ldskfsd dfjlsdjfsdaf dfasdaffd", activity=activities
        )
        Intentions.objects.create(intention="kdv dkjls dfaf", activity=activities)

        res = self.client.get(INTENTIONS_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        intentions_count = Intentions.objects.filter(activity=activities).count()

        self.assertEqual(intentions_count, 2)

    def test_retrieving_happenings_is_successful(self):
        """
        Test retrieving happenings is successful
        """
        activities = Activities.objects.create(
            name="ldskjfafd", journal_table=self.journal_table
        )

        Happenings.objects.create(
            happening="ldskfsd dfjlsdjfsdaf dfasdaffd", activity=activities
        )
        Happenings.objects.create(happening="kdv dkjls dfaf", activity=activities)

        res = self.client.get(HAPPENINGS_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        happenings_count = Happenings.objects.filter(activity=activities).count()

        self.assertEqual(happenings_count, 2)

    def test_retrieving_grateful_for_is_successful(self):
        """
        Test retrieving grateful_for is successful
        """
        activities = Activities.objects.create(
            name="ldskjfafd", journal_table=self.journal_table
        )

        GratefulFor.objects.create(
            grateful_for="ldskfsd dfjlsdjfsdaf dfasdaffd", activity=activities
        )
        GratefulFor.objects.create(grateful_for="kdv dkjls dfaf", activity=activities)

        res = self.client.get(GRATEFUL_FOR_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        grateful_for_count = GratefulFor.objects.filter(activity=activities).count()

        self.assertEqual(grateful_for_count, 2)

    def test_retrieving_action_items_for_is_successful(self):
        """
        Test retrieving action_items is successful
        """
        activities = Activities.objects.create(
            name="ldskjfafd", journal_table=self.journal_table
        )

        ActionItems.objects.create(
            action_item="ldskfsd dfjlsdjfsdaf dfasdaffd", activity=activities
        )
        ActionItems.objects.create(action_item="kdv dkjls dfaf", activity=activities)

        res = self.client.get(ACTION_ITEMS_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        action_items_count = ActionItems.objects.filter(activity=activities).count()

        self.assertEqual(action_items_count, 2)

    # tests retrieving sub model by another user fails
    def test_retrieving_intentions_by_current_user_for_another_user_fails(self):
        """
        Test that retrieving intentions by current user for another user fails
        """
        activities = Activities.objects.create(
            name="ldskjfafd", journal_table=self.journal_table
        )

        Intentions.objects.create(
            intention="ldskfsd dfjlsdjfsdaf dfasdaffd", activity=activities
        )
        Intentions.objects.create(intention="kdv dkjls dfaf", activity=activities)

        user_payload = {
            "first_name": "Test",
            "last_name": "User",
            "email": "user2@example.com",
            "username": "testuser",
            "password": "Awesomeuser123",
        }

        user = create_user(**user_payload)

        self.client.force_authenticate(user)
        res = self.client.get(INTENTIONS_URL)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.client.force_authenticate(self.user)
        self.assertEqual(res.data, [])

    def test_retrieving_happening_by_current_user_for_another_user_fails(self):
        """
        Test that retrieving happening by current user for another user fails
        """
        activities = Activities.objects.create(
            name="ldskjfafd", journal_table=self.journal_table
        )
        Happenings.objects.create(
            happening="ldskfsd dfjlsdjfsdaf dfasdaffd", activity=activities
        )
        Happenings.objects.create(happening="kdv dkjls dfaf", activity=activities)
        user_payload = {
            "first_name": "Test",
            "last_name": "User",
            "email": "user2@example.com",
            "username": "testuser",
            "password": "Awesomeuser123",
        }
        user = create_user(**user_payload)
        self.client.force_authenticate(user)
        res = self.client.get(HAPPENINGS_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.client.force_authenticate(self.user)
        self.assertEqual(res.data, [])

    def test_retrieving_grateful_for_by_current_user_for_another_user_fails(self):
        """
        Test that retrieving grateful_for by current user for another user fails
        """
        activities = Activities.objects.create(
            name="ldskjfafd", journal_table=self.journal_table
        )
        GratefulFor.objects.create(
            grateful_for="ldskfsd dfjlsdjfsdaf dfasdaffd", activity=activities
        )
        GratefulFor.objects.create(grateful_for="kdv dkjls dfaf", activity=activities)
        user_payload = {
            "first_name": "Test",
            "last_name": "User",
            "email": "user2@example.com",
            "username": "testuser",
            "password": "Awesomeuser123",
        }
        user = create_user(**user_payload)
        self.client.force_authenticate(user)
        res = self.client.get(GRATEFUL_FOR_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.client.force_authenticate(self.user)
        self.assertEqual(res.data, [])

    def test_retrieving_action_items_for_by_current_user_for_another_user_fails(self):
        """
        Test that retrieving action_items by current user for another user fails
        """
        activities = Activities.objects.create(
            name="ldskjfafd", journal_table=self.journal_table
        )
        ActionItems.objects.create(
            action_item="ldskfsd dfjlsdjfsdaf dfasdaffd", activity=activities
        )
        ActionItems.objects.create(action_item="kdv dkjls dfaf", activity=activities)
        user_payload = {
            "first_name": "Test",
            "last_name": "User",
            "email": "user2@example.com",
            "username":"testuser",
            "password": "Awesomeuser123",
        }
        user = create_user(**user_payload)
        self.client.force_authenticate(user)
        res = self.client.get(ACTION_ITEMS_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.client.force_authenticate(self.user)
        self.assertEqual(res.data, [])

    # test updating sub model full updating
    def test_updating_full_update_intentions_succeeds(self):
        """
        Test updating put update on the intentions succeeds
        """
        activities = Activities.objects.create(
            name="ldskjfafd", journal_table=self.journal_table
        )

        Intentions.objects.create(
            intention="ldskfsd dfjlsdjfsdaf dfasdaffd", activity=activities
        )
        intentions2 = Intentions.objects.create(
            intention="kdv dkjls dfaf", activity=activities
        )

        payload = {"intention": "kdvjl dkfjasdfa"}

        details_url = obj_detail_url("intentions", intentions2.id)

        res = self.client.put(details_url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(payload["intention"], res.data["intention"])

    def test_updating_full_update_happenings_succeeds(self):
        """
        Test updating put update on the happenings succeeds
        """
        activities = Activities.objects.create(
            name="ldskjfafd", journal_table=self.journal_table
        )

        Happenings.objects.create(
            happening="ldskfsd dfjlsdjfsdaf dfasdaffd", activity=activities
        )
        happening2 = Happenings.objects.create(
            happening="kdv dkjls dfaf", activity=activities
        )

        payload = {"happening": "kdvjl dkfjasdfa"}

        details_url = obj_detail_url("happenings", happening2.id)

        res = self.client.put(details_url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(payload["happening"], res.data["happening"])

    def test_updating_full_update_grateful_for_succeeds(self):
        """
        Test updating put update on the grateful_for succeeds
        """
        activities = Activities.objects.create(
            name="ldskjfafd", journal_table=self.journal_table
        )

        GratefulFor.objects.create(
            grateful_for="ldskfsd dfjlsdjfsdaf dfasdaffd", activity=activities
        )
        grateful_for2 = GratefulFor.objects.create(
            grateful_for="kdv dkjls dfaf", activity=activities
        )

        payload = {"grateful_for": "kdvjl dkfjasdfa"}

        details_url = obj_detail_url("gratefulfor", grateful_for2.id)

        res = self.client.put(details_url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(payload["grateful_for"], res.data["grateful_for"])

    def test_updating_full_update_action_items_succeeds(self):
        """
        Test updating put update on the action_items succeeds
        """
        activities = Activities.objects.create(
            name="ldskjfafd", journal_table=self.journal_table
        )

        ActionItems.objects.create(
            action_item="ldskfsd dfjlsdjfsdaf dfasdaffd", activity=activities
        )
        action_item2 = ActionItems.objects.create(
            action_item="kdv dkjls dfaf", activity=activities
        )

        payload = {"action_item": "kdvjl dkfjasdfa"}

        details_url = obj_detail_url("actionitems", action_item2.id)

        res = self.client.put(details_url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(payload["action_item"], res.data["action_item"])

    # tests partial_update of sub_models
    def test_partial_update_of_intentions_is_successful(self):
        """
        Test patch request of intentions is successful
        """
        activities = Activities.objects.create(
            name="ldskjfafd", journal_table=self.journal_table
        )

        Intentions.objects.create(
            intention="ldskfsd dfjlsdjfsdaf dfasdaffd", activity=activities
        )
        intentions2 = Intentions.objects.create(
            intention="kdv dkjls dfaf", activity=activities
        )

        payload = {"intention": "kdvjl dkfjasdfa"}

        details_url = obj_detail_url("intentions", intentions2.id)

        res = self.client.patch(details_url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(payload["intention"], res.data["intention"])

    def test_partial_update_of_happenings_is_successful(self):
        """
        Test patch request of happenings is successful
        """
        activities = Activities.objects.create(
            name="ldskjfafd", journal_table=self.journal_table
        )

        Happenings.objects.create(
            happening="ldskfsd dfjlsdjfsdaf dfasdaffd", activity=activities
        )
        happenings2 = Happenings.objects.create(
            happening="kdv dkjls dfaf", activity=activities
        )

        payload = {"happening": "kdvjl dkfjasdfa"}

        details_url = obj_detail_url("happenings", happenings2.id)

        res = self.client.patch(details_url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(payload["happening"], res.data["happening"])

    def test_partial_update_of_grateful_for_is_successful(self):
        """
        Test patch request of grateful_for is successful
        """
        activities = Activities.objects.create(
            name="ldskjfafd", journal_table=self.journal_table
        )

        GratefulFor.objects.create(
            grateful_for="ldskfsd dfjlsdjfsdaf dfasdaffd", activity=activities
        )
        grateful_for2 = GratefulFor.objects.create(
            grateful_for="kdv dkjls dfaf", activity=activities
        )
        payload = {"grateful_for": "kdvjl dkfjasdfa"}

        details_url = obj_detail_url("gratefulfor", grateful_for2.id)

        res = self.client.patch(details_url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(payload["grateful_for"], res.data["grateful_for"])

    def test_partial_update_of_action_items_for_is_successful(self):
        """
        Test patch request of action_items is successful
        """
        activities = Activities.objects.create(
            name="ldskjfafd", journal_table=self.journal_table
        )

        ActionItems.objects.create(
            action_item="ldskfsd dfjlsdjfsdaf dfasdaffd", activity=activities
        )
        action_items2 = ActionItems.objects.create(
            action_item="kdv dkjls dfaf", activity=activities
        )
        payload = {"action_item": "kdvjl dkfjasdfa"}

        details_url = obj_detail_url("actionitems", action_items2.id)

        res = self.client.patch(details_url, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(payload["action_item"], res.data["action_item"])

    def test_delete_of_intentions_is_successful(self):
        """
        Test deleting intentions is successful
        """
        activities = Activities.objects.create(
            name="ldskjfafd", journal_table=self.journal_table
        )

        Intentions.objects.create(
            intention="ldskfsd dfjlsdjfsdaf dfasdaffd", activity=activities
        )
        intentions2 = Intentions.objects.create(
            intention="kdv dkjls dfaf", activity=activities
        )

        details_url = obj_detail_url("intentions", intentions2.id)

        res = self.client.delete(details_url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        intentions_count = Intentions.objects.filter(activity=activities).count()

        self.assertEqual(intentions_count, 1)

    def test_delete_of_happenings_is_successful(self):
        """
        Test deleting happenings is successful
        """
        activities = Activities.objects.create(
            name="ldskjfafd", journal_table=self.journal_table
        )

        Happenings.objects.create(
            happening="ldskfsd dfjlsdjfsdaf dfasdaffd", activity=activities
        )
        happenings2 = Happenings.objects.create(
            happening="kdv dkjls dfaf", activity=activities
        )

        details_url = obj_detail_url("happenings", happenings2.id)

        res = self.client.delete(details_url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        happening_count = Happenings.objects.filter(activity=activities).count()

        self.assertEqual(happening_count, 1)

    def test_delete_of_grateful_for_is_successful(self):
        """
        Test deleting grateful_for is successful
        """
        activities = Activities.objects.create(
            name="ldskjfafd", journal_table=self.journal_table
        )

        GratefulFor.objects.create(
            grateful_for="ldskfsd dfjlsdjfsdaf dfasdaffd", activity=activities
        )
        grateful_for2 = GratefulFor.objects.create(
            grateful_for="kdv dkjls dfaf", activity=activities
        )

        details_url = obj_detail_url("gratefulfor", grateful_for2.id)

        res = self.client.delete(details_url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        grateful_for_count = GratefulFor.objects.filter(activity=activities).count()

        self.assertEqual(grateful_for_count, 1)

    def test_delete_of_action_items_is_successful(self):
        """
        Test deleting action_items is successful
        """
        activities = Activities.objects.create(
            name="ldskjfafd", journal_table=self.journal_table
        )

        ActionItems.objects.create(
            action_item="ldskfsd dfjlsdjfsdaf dfasdaffd", activity=activities
        )
        action_items2 = ActionItems.objects.create(
            action_item="kdv dkjls dfaf", activity=activities
        )

        details_url = obj_detail_url("actionitems", action_items2.id)

        res = self.client.delete(details_url)

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)

        action_items_count = ActionItems.objects.filter(activity=activities).count()

        self.assertEqual(action_items_count, 1)
