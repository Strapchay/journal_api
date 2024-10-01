"""
Views For the Journal
"""
from user.authentication import ExpiringTokenAuthentication
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiExample,
    OpenApiResponse,
)
from rest_framework import viewsets, mixins, status
from rest_framework.response import Response
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.exceptions import ValidationError
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from core.models import (
    Journal,
    JournalTables,
    Tags,
    Activities,
    Intentions,
    ActionItems,
    Happenings,
    GratefulFor,
)
from journal import serializers
from journal.mixins import (
    BatchRouteMixin,
    BatchUpdateActivitiesRouteMixin,
    BatchDeleteActivitiesRouteMixin,
    BatchDuplicateActivitiesRouteMixin,
    BatchTagRouteMixin,
    BatchSubmodelRouteMixin,
)
from journal.exceptions import RequestDenied


class JournalViewSet(viewsets.ModelViewSet):
    """
    Viewset for creating journal
    """

    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = serializers.JournalSerializer
    permission_classes = [IsAuthenticated]
    queryset = Journal.objects.all()
    http_method_names = ["put", "patch", "post", "get"]

    def get_queryset(self):
        """
        Filter queryset to authenticated user
        """
        queryset = self.queryset
        return queryset.filter(user=self.request.user)

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)


@extend_schema_view(
    create=extend_schema(
        description="Endpoint for creating a journal table",
        examples=[
            OpenApiExample("Request Body", value={"journal": 1, "table_name": "string"})
        ],
    )
)
class JournalTableViewSet(viewsets.ModelViewSet):
    """
    Viewset for creating journal table
    """

    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = serializers.JournalTableSerializer
    permission_classes = [IsAuthenticated]
    queryset = JournalTables.objects.all()

    def perform_create(self, serializer):
        """
        Create a new journal table
        """
        journal = get_object_or_404(Journal, id=self.request.data.get("journal"))

        if journal is not None:
            serializer.save(journal=journal)

    def perform_destroy(self, instance):
        instance_id = instance.id
        user_journal = Journal.objects.get(user=self.request.user)
        user_journal_tables = JournalTables.objects.filter(journal=user_journal)

        if user_journal.current_table == instance_id:
            if user_journal_tables.count() > 1:
                instance.delete()
                print("user jor current tab to set to", user_journal_tables.first().id)
                user_journal.current_table = user_journal_tables.first().id
                user_journal.save()

            else:
                raise RequestDenied()
        else:
            if user_journal_tables.count() > 1:
                instance.delete()
            else:
                raise RequestDenied()

    def retrieve(self, request, *args, **kwargs):
        try:
            queryset = self.get_object()
            serializer = self.get_serializer(queryset)
            return Response(serializer.data, status=status.HTTP_200_OK)
        except Exception as e:
            raise ValidationError(e)

    def get_queryset(self):
        """
        Filter queryset to authenticated user
        """
        # if id is not None:
        #     return self.queryset.filter(journal__user=self.request.user, id=id)

        queryset = self.queryset
        return queryset.filter(journal__user=self.request.user)


@extend_schema_view(
    create=extend_schema(
        description="""
        Endpoint to create Tags.
        For the tag_color the following Enums are available:

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

        For the tag_class the following Enums are available:

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

        Note: The tag_class should be relative to the choosen tag_color
        """,
        examples=[
            OpenApiExample(
                "Request Body",
                value={
                    "tag_name": "string",
                    "tag_color": "OFF GRAY",
                    "tag_class": "color-gray",
                },
            ),
            OpenApiExample(
                "Response Body",
                value={
                    "id": 0,
                    "tag_user": 0,
                    "tag_name": "string",
                    "tag_color": "OFF GRAY",
                    "tag_class": "color-gray",
                },
            ),
        ],
    ),
    update=extend_schema(
        description="Endpoint to update Tags",
        examples=[
            OpenApiExample(
                "Request Body",
                value={
                    "tag_name": "string",
                    "tag_color": "OFF GRAY",
                    "tag_class": "color-gray",
                },
            ),
            OpenApiExample(
                "Response Body",
                value={
                    "id": 0,
                    "tag_user": 0,
                    "tag_name": "string",
                    "tag_color": "OFF GRAY",
                    "tag_class": "color-gray",
                },
            ),
        ],
    ),
    partial_update=extend_schema(
        description="Endpoint to update Tags",
        examples=[
            OpenApiExample(
                "Request Body",
                value={
                    "tag_name": "string",
                    "tag_color": "OFF GRAY",
                    "tag_class": "color-gray",
                },
            ),
            OpenApiExample(
                "Response Body",
                value={
                    "id": 0,
                    "tag_user": 0,
                    "tag_name": "string",
                    "tag_color": "OFF GRAY",
                    "tag_class": "color-gray",
                },
            ),
        ],
    ),
    batch_tag_processor=extend_schema(exclude=True),
)
class TagsViewSet(BatchRouteMixin, BatchTagRouteMixin, viewsets.ModelViewSet):
    """
    Viewset for creating journal table
    """

    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = serializers.TagsSerializer
    permission_classes = [IsAuthenticated]
    queryset = Tags.objects.all()

    def perform_create(self, serializer):
        """
        Create a new journal table
        """
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)

    def get_queryset(self, ids=None):
        """
        Filter queryset to authenticated user
        """
        queryset = self.queryset
        if ids is not None:
            return queryset.filter(
                tag_user=self.request.user,
                id__in=ids,
            )

        return queryset.filter(
            Q(tag_user=self.request.user) | Q(tag_user__is_superuser=True)
        )


@extend_schema_view(
    create=extend_schema(
        description="Endpoint to create an Activity. The tags to use can be the default tags by making a get request to the tags endpoint or by creating a new tags to use",
        examples=[
            OpenApiExample(
                "Request Body",
                value={
                    "name": "string",
                    "tags": [0, 2],
                    "journal_table": 5,
                },
            )
        ],
    ),
    update=extend_schema(
        description="Endpoint for Updating an Activity",
        examples=[
            OpenApiExample(
                "Request Body",
                value={
                    "name": "string",
                    "tags": [1, 2],
                },
            ),
        ],
    ),
    partial_update=extend_schema(
        description="Endpoint for Updating an Activity",
        examples=[
            OpenApiExample(
                "Request Body",
                value={
                    "name": "string",
                    "tags": [1, 2],
                },
            ),
            OpenApiExample(
                "Batch Add Tags Activities Body",
                description="Allows for updating the tags for each activity to similar tags",
                value={
                    "activities_list": [{"ids": [1, 2, 3], "tags": [1, 2, 3]}],
                },
            ),
            OpenApiExample(
                "Add and update submodels of an Activity",
                description="To create and update an Activity, the request body is in this format. For the `create` key. The `relative_item` specifies the order in which the submodel to be created should be ordered against. The `ordering_list` specifies the updated ordering of each created submodel field excluding the ordering for the submodel instance to be created. The `update` key contains the submodel instance to update which in most cases is the relative_item of the submodel to create. The `update_and_create` should be True if an update and create operation is to be performed. The `type` specifies the submodel type",
                value={
                    "intentions": {
                        "activity": 1,
                        "create": {
                            "intention": "string",
                            "relative_item": 1,
                            "ordering": 2,
                        },
                        "update": {"id": 1, "intention": "string"},
                        "ordering_list": [
                            {"id": 1, "ordering": 1},
                            {"id": 2, "ordering": 3},
                            {"id": 3, "ordering": 4},
                        ],
                        "update_and_create": True,
                        "type": "intentions",
                    }
                },
            ),
            OpenApiExample(
                "Update submodels of an Activity",
                description="The `update` key contains the submodel instance to update. The `update_only` should be True if an update operation is to be performed. The type specifies the submodel type",
                value={
                    "intentions": {
                        "activity": 1,
                        "update": {"id": 1, "intention": "string"},
                        "update_only": True,
                        "type": "intentions",
                    }
                },
            ),
            OpenApiExample(
                "Update submodels of an Activity",
                description="The `update_action_item_checked` key contains the checked state of an action_item instance,its id and the `update_checked` specifies the checked state of the instance should be updated. The `update_only` should be True if an update operation is to be performed",
                value={
                    "action_items": {
                        "activity": 1,
                        "update_action_item_checked": {
                            "checked": True,
                            "id": 2,
                            "update_checked": True,
                            "type": "action_items",
                        },
                    }
                },
            ),
        ],
    ),
    batch_duplicate_activities=extend_schema(
        description="Endpoint for Batch Duplicating Activities",
        examples=[
            OpenApiExample(
                "Duplicate Activities Body",
                description="Allows for batch duplication of activities.The `ids` contains the id of each activity to duplicate",
                value={
                    "duplicate_list": [{"ids": [1, 2, 3]}],
                },
            ),
        ],
    ),
    batch_delete_activities=extend_schema(
        description="Endpoint for Batch Deleting Activities",
        examples=[
            OpenApiExample(
                "Batch Delete Activities Body",
                description="Allows for batch delete of activities.The id of each activity should be supplied in the list",
                value={
                    "delete_list": [1, 2, 3],
                },
            ),
        ],
    ),
)
class ActivitiesViewSet(
    BatchRouteMixin,
    BatchUpdateActivitiesRouteMixin,
    BatchDeleteActivitiesRouteMixin,
    BatchDuplicateActivitiesRouteMixin,
    viewsets.ModelViewSet,
):
    """
    Viewset for creating a journal table activities
    """

    authentication_classes = [ExpiringTokenAuthentication]
    serializer_class = serializers.ActivitiesSerializer
    permission_classes = [IsAuthenticated]
    queryset = Activities.objects.all()

    def perform_create(self, serializer):
        serializer.save()

    def get_queryset(self, ids=None):
        if self.request.user.is_authenticated:
            if ids:
                return self.queryset.filter(
                    journal_table__journal__user=self.request.user, id__in=ids
                )

            return self.queryset.filter(journal_table__journal__user=self.request.user)


@extend_schema_view(
    batch_submodel_processor=extend_schema(exclude=True),
)
class BaseSubModelsViewSet(
    BatchRouteMixin, BatchSubmodelRouteMixin, viewsets.ModelViewSet
):
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [IsAuthenticated]

    def perform_create(self, serializer):
        if self.request.user.is_authenticated:
            serializer.save()

    def get_queryset(self):
        if self.request.user.is_authenticated:
            return self.queryset.filter(
                activity__journal_table__journal__user=self.request.user
            )


@extend_schema_view(
    update=extend_schema(
        description="Endpoint for Updating an Intentions Item",
        examples=[
            OpenApiExample(
                "Request Body",
                value={
                    "intention": "string",
                },
            ),
            OpenApiExample(
                "Response Body",
                value={
                    "id": 1,
                    "intention": "string",
                    "activity": 1,
                },
            ),
        ],
    ),
    partial_update=extend_schema(
        description="Endpoint for Updating an Intentions Item",
        examples=[
            OpenApiExample(
                "Request Body",
                value={
                    "intention": "string",
                },
            ),
            OpenApiExample(
                "Response Body",
                value={
                    "id": 1,
                    "intention": "string",
                    "activity": 1,
                },
            ),
        ],
    ),
)
class IntentionsViewSet(BaseSubModelsViewSet):
    serializer_class = serializers.IntentionsSerializer
    queryset = Intentions.objects.all()


@extend_schema_view(
    update=extend_schema(
        description="Endpoint for Updating an Happenings Item",
        examples=[
            OpenApiExample(
                "Request Body",
                value={
                    "happening": "string",
                },
            ),
            OpenApiExample(
                "Response Body",
                value={
                    "id": 1,
                    "happening": "string",
                    "activity": 1,
                },
            ),
        ],
    ),
    partial_update=extend_schema(
        description="Endpoint for Updating an Happening Item",
        examples=[
            OpenApiExample(
                "Request Body",
                value={
                    "happening": "string",
                },
            ),
            OpenApiExample(
                "Response Body",
                value={
                    "id": 1,
                    "happening": "string",
                    "activity": 1,
                },
            ),
        ],
    ),
)
class HappeningsViewSet(BaseSubModelsViewSet):
    serializer_class = serializers.HappeningsSerializer
    queryset = Happenings.objects.all()


@extend_schema_view(
    update=extend_schema(
        description="Endpoint for Updating an Grateful For Item",
        examples=[
            OpenApiExample(
                "Request Body",
                value={
                    "grateful_for": "string",
                },
            ),
            OpenApiExample(
                "Response Body",
                value={
                    "id": 1,
                    "grateful_for": "string",
                    "activity": 1,
                },
            ),
        ],
    ),
    partial_update=extend_schema(
        description="Endpoint for Updating an Activity",
        examples=[
            OpenApiExample(
                "Request Body",
                value={
                    "grateful_for": "string",
                },
            ),
            OpenApiExample(
                "Response Body",
                value={
                    "id": 1,
                    "grateful_for": "string",
                    "activity": 1,
                },
            ),
        ],
    ),
)
class GratefulForViewSet(BaseSubModelsViewSet):
    serializer_class = serializers.GratefulForSerializer
    queryset = GratefulFor.objects.all()


@extend_schema_view(
    update=extend_schema(
        description="Endpoint for Updating an ActionItems Item",
        examples=[
            OpenApiExample(
                "Request Body",
                value={
                    "action_item": "string",
                },
            ),
            OpenApiExample(
                "Response Body",
                value={
                    "id": 1,
                    "action_item": "string",
                    "activity": 1,
                },
            ),
        ],
    ),
    partial_update=extend_schema(
        description="Endpoint for Updating an ActionItems Item",
        examples=[
            OpenApiExample(
                "Request Body",
                value={
                    "action_item": "string",
                },
            ),
            OpenApiExample(
                "Response Body",
                value={
                    "id": 1,
                    "action_item": "string",
                    "activity": 1,
                },
            ),
        ],
    ),
)
class ActionsItemViewSet(BaseSubModelsViewSet):
    serializer_class = serializers.ActionItemsSerializer
    queryset = ActionItems.objects.all()
