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
from core.models import (
    Journal,
    Tags,
    Activities,
    JournalTables,
    Intentions,
    Happenings,
    ActionItems,
    GratefulFor,
)
from journal.serializers import ActivitiesSerializer
from django.db.models import Q
import json
from collections import Counter

ACTIVITIES_URL = reverse("journal:activities-list")
BATCH_UPDATE_ACTIVITIES_URL = reverse("journal:activities-batch_update_activities")
BATCH_DELETE_ACTIVITIES_URL = reverse("journal:activities-batch_delete_activities")
BATCH_DUPLICATE_ACTIVITIES_URL = reverse(
    "journal:activities-batch_duplicate_activities"
)
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

    def test_create_activities_creates_default_submodels(self):
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

        activity = Activities.objects.filter(journal_table=journal_table).first()

        intention = Intentions.objects.filter(activity=activity).count()
        happening = Happenings.objects.filter(activity=activity).count()
        action_item = ActionItems.objects.filter(activity=activity).count()
        grateful_for = GratefulFor.objects.filter(activity=activity).count()

        total_submodels = intention + happening + action_item + grateful_for

        self.assertEqual(total_submodels, 4)

    def test_create_activities_submodel_auto_increments_ordering(self):
        """
        Test create activities submodels auto-increments submodels field
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

        activity = Activities.objects.filter(journal_table=journal_table).first()

        Intentions.objects.create(activity=activity, intention="ksldjdfjlsdjd")

        intention = Intentions.objects.filter(activity=activity).count()

        activity_url = detail_url(activity.id)
        activity_res = self.client.get(activity_url)
        self.assertEqual(activity_res.status_code, status.HTTP_200_OK)
        activities_intentions = activity_res.data["intentions"]
        ordering_list = [1, 2]
        for i in activities_intentions:
            self.assertIn(i["ordering"], ordering_list)

    def test_create_activities_relative_item_updates_other_activities_ordering(self):
        """
        Test creating an activity relative to another activity increments and reorders the activities
        """

        journal_table = JournalTables.objects.create(
            table_name="New Table", journal=self.journal
        )

        activities1 = Activities.objects.create(
            name="Kdf sfsdf",
            journal_table=journal_table,
        )
        activities2 = Activities.objects.create(
            name="Kdf okvs",
            journal_table=journal_table,
        )
        activities3 = Activities.objects.create(
            name="Kdf ovpsa",
            journal_table=journal_table,
        )

        create_relative_activities_payload = {
            "name": "",
            "journal_table": journal_table.id,
            "ordering_list": {
                "create_item_ordering": 2,
                "table_items_ordering": [
                    {"id": activities1.id, "ordering": 1},
                    {"id": activities2.id, "ordering": 3},
                    {"id": activities3.id, "ordering": 4},
                ],
            },
        }

        self.client.force_authenticate(self.user)

        res = self.client.post(
            ACTIVITIES_URL, create_relative_activities_payload, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        activities = Activities.objects.filter(journal_table=journal_table)
        activity1 = activities.first()
        self.assertEqual(activity1.ordering, 1)
        self.assertEqual(activities.count(), 4)
        self.assertEqual(res.data["ordering"], 2)

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

    def test_partial_update_of_a_submodel_activity(self):
        """
        Test a patch update of an activity submodel
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

        submodel_payload = {
            "intentions": {
                "activity": activities.id,
                "create": {"intention": "lkdsjflkdfdfs"},
                "update": {"id": None, "intention": "kdlfjiodfsdf"},
                "update_and_create": True,
                "type": "intentions",
            }
        }

        activities_url = detail_url(activities.id)
        res = self.client.patch(activities_url, submodel_payload, format="json")
        activities.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["intentions"]), 2)

    def test_partial_update_of_a_submodel_activity_grateful_for(self):
        """
        Test a patch update of an activity grateful_for submodel
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

        submodel_payload = {
            "grateful_for": {
                "activity": activities.id,
                "create": {"grateful_for": "lkdsjflkdfdfs"},
                "update": {"id": None, "grateful_for": "kdlfjiodfsdf"},
                "update_and_create": True,
                "type": "grateful_for",
            }
        }

        activities_url = detail_url(activities.id)
        res = self.client.patch(activities_url, submodel_payload, format="json")
        activities.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["grateful_for"]), 2)

    def test_partial_update_of_an_activity_submodel_activity(self):
        """
        Test a patch update of a submodel from the activity
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
        intention_upd = Intentions.objects.create(
            intention="created inteention", activity=activities
        )

        submodel_payload = {
            "intentions": {
                "activity": activities.id,
                "update": {"id": intention_upd.id, "intention": "kdlfjiodfsdf"},
                "update_only": True,
                "type": "intentions",
            }
        }

        activities_url = detail_url(activities.id)
        res = self.client.patch(activities_url, submodel_payload, format="json")
        activities.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(len(res.data["intentions"]), 1)
        self.assertEqual(
            res.data["intentions"][0]["intention"],
            submodel_payload["intentions"]["update"]["intention"],
        )

    def test_partial_update_of_an_activity_action_item_checked_update(self):
        """
        Test a patch update of an activity action_item checked states gets updated successfully
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

        action_item = ActionItems.objects.create(
            action_item="dfaddfsdf", activity=activities
        )
        # todo add actionItem checked payload
        submodel_payload = {
            "action_items": {
                "activity": activities.id,
                "update_action_item_checked": {
                    "checked": True,
                    "id": action_item.id,
                    "update_checked": True,
                    "type": "action_items",
                },
            }
        }

        activities_url = detail_url(activities.id)
        res = self.client.patch(activities_url, submodel_payload, format="json")
        action_item.refresh_from_db()
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(action_item.checked, True)

    def test_partial_update_of_a_submodel_activity_creates_and_reorders_ordering(self):
        """
        Test a create and update of an activity submodel with ordering and relative item specified reorders the submodel in relation to its relative item and updates items
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

        intention1 = Intentions.objects.create(
            activity=activities, intention="skdfljdff", ordering=1
        )
        intention2 = Intentions.objects.create(
            activity=activities, intention="lkvposafs", ordering=2
        )
        intention3 = Intentions.objects.create(
            activity=activities, intention="kvp[sadofsd]", ordering=3
        )

        submodel_payload = {
            "intentions": {
                "activity": activities.id,
                "create": {
                    "intention": "lkdsjflkdfdfs",
                    "relative_item": intention2.id,
                    "ordering": 3,
                },
                "update": {"id": intention2.id, "intention": "mod"},
                "ordering_list": [
                    {"id": intention1.id, "ordering": 1},
                    {"id": intention2.id, "ordering": 2},
                    {"id": intention3.id, "ordering": 4},
                ],
                "update_and_create": True,
                "type": "intentions",
            }
        }
        # ordering for item to create get from max
        activities_url = detail_url(activities.id)
        res = self.client.patch(activities_url, submodel_payload, format="json")
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        activities_intentions = json.loads(json.dumps(res.data["intentions"]))
        created_intention_id = None
        for i in activities_intentions:
            if i["intention"] == submodel_payload["intentions"]["create"]["intention"]:
                created_intention_id = i["id"]
        activities.refresh_from_db()
        intentions_list = (
            Intentions.objects.filter(activity=activities)
            .order_by("ordering")
            .values_list("id", flat=True)
        )
        expected_ordering_list = [
            intention1.id,
            intention2.id,
            created_intention_id,
            intention3.id,
        ]
        self.assertEqual(expected_ordering_list, list(intentions_list))

    def test_batch_update_activities_tags(self):
        """
        Test a batch update of multiple activities tags by
        assigning multiple same tags to the activ"ties
        """
        journal_table = JournalTables.objects.create(
            table_name="New Table", journal=self.journal
        )

        tag1 = Tags.objects.create(
            tag_name="plvpdsf",
            tag_user=self.user,
            tag_color=Tags.Colors.RED,
            tag_class=Tags.ColorsClasses.RED_CLASS,
        )
        tag2 = Tags.objects.create(
            tag_name="p[ovad]",
            tag_user=self.user,
            tag_color=Tags.Colors.GRAY,
            tag_class=Tags.ColorsClasses.GRAY_CLASS,
        )

        tag3 = Tags.objects.create(
            tag_name="kdadff",
            tag_user=self.user,
            tag_color=Tags.Colors.GRAY,
            tag_class=Tags.ColorsClasses.GRAY_CLASS,
        )

        activities1 = Activities.objects.create(
            name="Kdf sfsdf",
            journal_table=journal_table,
        )
        activities2 = Activities.objects.create(
            name="Kdf okvs",
            journal_table=journal_table,
        )
        activities3 = Activities.objects.create(
            name="Kdf ovpsa",
            journal_table=journal_table,
        )

        activities1.tags.add(self.tag1)
        activities1.tags.add(self.tag2)
        self.client.force_authenticate(self.user)

        batch_update_payload = {
            "activities_list": [
                {
                    "ids": [activities1.id, activities2.id, activities3.id],
                    "tags": [tag1.id, tag2.id, tag3.id],
                }
            ]
        }
        res = self.client.patch(
            BATCH_UPDATE_ACTIVITIES_URL, batch_update_payload, format="json"
        )

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        for i in [activities1, activities2, activities3]:
            self.assertEqual(list(i.tags.all()), [tag1, tag2, tag3])

    def test_batch_delete_activities(self):
        """
        Test a batch delete of multiple activities
        """
        journal_table = JournalTables.objects.create(
            table_name="New Table", journal=self.journal
        )

        activities1 = Activities.objects.create(
            name="Kdf sfsdf",
            journal_table=journal_table,
        )
        activities2 = Activities.objects.create(
            name="Kdf okvs",
            journal_table=journal_table,
        )
        activities3 = Activities.objects.create(
            name="Kdf ovpsa",
            journal_table=journal_table,
        )

        self.client.force_authenticate(self.user)

        batch_delete_payload = {
            "delete_list": [activities1.id, activities2.id, activities3.id],
        }
        res = self.client.delete(
            BATCH_DELETE_ACTIVITIES_URL, batch_delete_payload, format="json"
        )

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        activities_count = Activities.objects.filter(
            journal_table=journal_table
        ).count()
        self.assertEqual(activities_count, 0)

    def test_batch_duplicate_activities(self):
        """
        Test duplicating multiple activities is successful
        """
        journal_table = JournalTables.objects.create(
            table_name="New Table", journal=self.journal
        )

        activities1 = Activities.objects.create(
            name="Kdf sfsdf",
            journal_table=journal_table,
        )
        activities2 = Activities.objects.create(
            name="Kdf okvs",
            journal_table=journal_table,
        )
        activities3 = Activities.objects.create(
            name="Kdf ovpsa",
            journal_table=journal_table,
        )

        self.client.force_authenticate(self.user)

        batch_delete_payload = {
            "delete_list": [activities1.id, activities2.id, activities3.id],
        }
        res = self.client.delete(
            BATCH_DELETE_ACTIVITIES_URL, batch_delete_payload, format="json"
        )

        self.assertEqual(res.status_code, status.HTTP_204_NO_CONTENT)
        activities_count = Activities.objects.filter(
            journal_table=journal_table
        ).count()
        self.assertEqual(activities_count, 0)

    def test_batch_duplicate_activities(self):
        """
        Test a batch duplicate of multiple activities
        """
        journal_table = JournalTables.objects.create(
            table_name="New Table", journal=self.journal
        )

        tag1 = Tags.objects.create(
            tag_name="plvpdsf",
            tag_user=self.user,
            tag_color=Tags.Colors.RED,
            tag_class=Tags.ColorsClasses.RED_CLASS,
        )
        tag2 = Tags.objects.create(
            tag_name="p[ovad]",
            tag_user=self.user,
            tag_color=Tags.Colors.GRAY,
            tag_class=Tags.ColorsClasses.GRAY_CLASS,
        )

        tag3 = Tags.objects.create(
            tag_name="kdadff",
            tag_user=self.user,
            tag_color=Tags.Colors.GRAY,
            tag_class=Tags.ColorsClasses.GRAY_CLASS,
        )

        activities1 = Activities.objects.create(
            name="Kdf sfsdf",
            journal_table=journal_table,
        )
        activities2 = Activities.objects.create(
            name="Kdf okvs",
            journal_table=journal_table,
        )
        activities3 = Activities.objects.create(
            name="Kdf ovpsa",
            journal_table=journal_table,
        )

        activities1.tags.add(tag1)
        activities2.tags.add(tag1, tag2)
        activities3.tags.add(tag1, tag2, tag3)

        self.client.force_authenticate(self.user)

        batch_duplicate_payload = {
            "duplicate_list": [
                {"ids": [activities1.id, activities2.id, activities3.id]}
            ],
        }
        res = self.client.post(
            BATCH_DUPLICATE_ACTIVITIES_URL, batch_duplicate_payload, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        activities = Activities.objects.filter(journal_table=journal_table)
        activities_id_unique = activities.values_list("id", flat=True)
        activities_count = activities.count()
        activities_relate_count = Activities.objects.filter(
            name=activities1.name
        ).count()
        unique_items = Counter(activities_id_unique)
        for i in unique_items:
            self.assertEqual(unique_items[i], 1)
        self.assertEqual(list(activities_id_unique), list(unique_items.keys()))
        self.assertEqual(activities_count, 6)
        self.assertEqual(activities_relate_count, 2)

    def test_batch_duplicate_activities_duplicates_tags(self):
        """
        Test a batch duplicate of multiple activities also duplicates its tags
        """
        journal_table = JournalTables.objects.create(
            table_name="New Table", journal=self.journal
        )

        tag1 = Tags.objects.create(
            tag_name="plvpdsf",
            tag_user=self.user,
            tag_color=Tags.Colors.RED,
            tag_class=Tags.ColorsClasses.RED_CLASS,
        )
        tag2 = Tags.objects.create(
            tag_name="p[ovad]",
            tag_user=self.user,
            tag_color=Tags.Colors.GRAY,
            tag_class=Tags.ColorsClasses.GRAY_CLASS,
        )

        tag3 = Tags.objects.create(
            tag_name="kdadff",
            tag_user=self.user,
            tag_color=Tags.Colors.GRAY,
            tag_class=Tags.ColorsClasses.GRAY_CLASS,
        )

        activities1 = Activities.objects.create(
            name="Kdf sfsdf",
            journal_table=journal_table,
        )
        activities2 = Activities.objects.create(
            name="Kdf okvs",
            journal_table=journal_table,
        )
        activities3 = Activities.objects.create(
            name="Kdf ovpsa",
            journal_table=journal_table,
        )

        Intentions.objects.create(activity=activities1, intention="dklvjosadadf")
        GratefulFor.objects.create(activity=activities2, grateful_for="kdvoasdfdf")
        Happenings.objects.create(activity=activities3, happening="vodfsfjoasdfad")
        activities1.tags.add(tag1)
        activities2.tags.add(tag1, tag2)
        activities3.tags.add(tag1, tag2, tag3)

        self.client.force_authenticate(self.user)

        batch_duplicate_payload = {
            "duplicate_list": [
                {"ids": [activities1.id, activities2.id, activities3.id]}
            ],
        }
        res = self.client.post(
            BATCH_DUPLICATE_ACTIVITIES_URL, batch_duplicate_payload, format="json"
        )
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        activities = Activities.objects.filter(journal_table=journal_table)
        activities_id_unique = activities.values_list("id", flat=True)
        activities_count = activities.count()
        activities_relate_count = Activities.objects.filter(
            name=activities1.name
        ).count()
        activities_serializer = ActivitiesSerializer(activities, many=True)
        unique_items = Counter(activities_id_unique)
        for i in unique_items:
            self.assertEqual(unique_items[i], 1)
        self.assertEqual(list(activities_id_unique), list(unique_items.keys()))

        # self.assertEqual(list(set(activities_id_unique)), list(activities_id_unique))
        self.assertEqual(activities_count, 6)
        self.assertEqual(activities_relate_count, 2)
        other_activity = Activities.objects.filter(name=activities3.name)
        other_activity_1 = other_activity.first()
        other_activity_2 = other_activity.last()
        self.assertEqual(
            other_activity_1.tags.all().count(), other_activity_2.tags.all().count()
        )
