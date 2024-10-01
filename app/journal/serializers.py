"""
Serializers for Journal APIs
"""
from rest_framework import serializers, exceptions
from core.models import (
    Journal,
    JournalTables,
    Tags,
    Activities,
    ActionItems,
    Happenings,
    Intentions,
    GratefulFor,
)
from journal.mixins import (
    BatchUpdateActivitiesSerializerMixin,
    BatchDuplicateActivitiesSerializerMixin,
    BatchTagSerializerMixin,
    BatchSubmodelSerializerMixin,
    CloneModelMixin,
    TagsValidatorMixin,
    SubmodelMixin,
)


from django.db.models import Q
from django.db import IntegrityError
from django.http import QueryDict
import copy
from journal.config import get_table_defaults, SUBMODELS_LIST
import copy
from collections import OrderedDict
import time


class BatchUpdateActivitiesSerializer(
    serializers.ListSerializer, BatchUpdateActivitiesSerializerMixin
):
    """
    Serializer for Activities for updating batch activities
    """

    def update(self, instance, validated_data):
        """
        Update Activities Items
        """
        tag_list = validated_data[0].pop("tags", None)
        tags_instance = Tags.objects.filter(id__in=tag_list)
        obj_result = []
        for i, instance_obj in enumerate(instance):
            instance_obj.tags.clear()
            instance_obj.tags.add(*tags_instance)

        return instance

    class Meta:
        fields = [
            "id",
            "name",
            "tags",
            "journal_table",
            "intentions",
            "happenings",
            "grateful_for",
            "action_items",
            "ordering",
        ]


class BatchTagSerializer(
    TagsValidatorMixin, BatchTagSerializerMixin, serializers.ListSerializer
):
    """
    Serializer for batch related actions for tags
    """

    def validate(self, attrs):
        return self.validate_for_multiple_tags(attrs)

    def create(self, validated_data):
        user = self.context["request"].user
        tag_list = validated_data

        create_tag_list = []
        if tag_list is not None:
            for tag in tag_list:
                tag.pop("user", None)
                tag["tag_user"] = user
                create_tag_list.append(self.child.Meta.model(**tag))

        try:
            self.child.Meta.model.objects.bulk_create(create_tag_list)
        except IntegrityError as e:
            raise serializers.ValidationError(detail=e)

        return create_tag_list

    def update(self, instance, validated_data):
        try:
            instance_list = instance
            for i, instance in enumerate(instance_list):
                for attr, value in validated_data[i].items():
                    if value is not None:
                        setattr(instance, attr, value)

            try:
                self.child.Meta.model.objects.bulk_update(
                    instance_list, ["tag_name", "tag_color", "tag_class"]
                )
            except IntegrityError as e:
                raise serializers.ValidationError(detail=e)

            return instance_list
        except Exception as e:
            raise exceptions.ValidationError(detail=e)


class BatchSubmodelSerializer(
    SubmodelMixin, BatchSubmodelSerializerMixin, serializers.ListSerializer
):
    """
    Serializer for batch related actions for submodels
    """

    def validate(self, attrs):
        pass

    def create(self, validated_data):
        pass

    def update(self, instance, validated_data):
        pass


class BatchDuplicateActivitiesSerializer(
    CloneModelMixin,
    BatchDuplicateActivitiesSerializerMixin,
    serializers.ListSerializer,
):
    """
    Serializer for Activities for duplicating batch activities
    """

    def create(self, validated_data):
        """
        Create Duplicated Activities Items
        """
        activities_to_duplicate = Activities.objects.filter(
            id__in=validated_data[0]["ids"]
        )
        start_time = time.time()
        duplicates_to_create = [
            self.duplicate_model(activity) for activity in activities_to_duplicate
        ]

        end_time = time.time()
        total = end_time - start_time
        return duplicates_to_create

    class Meta:
        fields = [
            "id",
            "name",
            "tags",
            "journal_table",
            "intentions",
            "happenings",
            "grateful_for",
            "action_items",
            "ordering",
        ]


class ListSerializerClassInitMixin:
    list_serializer_type_classes = {
        "batch_update_activities": BatchUpdateActivitiesSerializer,
        "batch_duplicate_activities": BatchDuplicateActivitiesSerializer,
        "batch_tag_processor": BatchTagSerializer,
    }

    def __init__(self, *args, **kwargs) -> None:
        list_serializer_type = kwargs.pop("type", None)
        super().__init__(*args, **kwargs)

        if list_serializer_type is not None:
            self.Meta.list_serializer_class = self.list_serializer_type_classes[
                list_serializer_type
            ]


class TagsSerializer(TagsValidatorMixin, serializers.ModelSerializer):
    """
    Serializer for serializing the Tags
    """

    def validate(self, attrs):
        try:
            return self.validate_for_single_tag(attrs)
        except KeyError as e:
            raise exceptions.ValidationError(detail="Invalid Update data provided")

    def create(self, validated_data):
        user = validated_data.pop("tag_user", self.context["request"].user)

        tag = Tags.objects.create(
            tag_user=user,
            tag_name=validated_data["tag_name"],
            tag_color=validated_data["tag_color"],
            tag_class=validated_data["tag_class"],
        )
        return tag

    class Meta:
        list_serializer_class = BatchTagSerializer
        model = Tags
        fields = ["id", "tag_user", "tag_name", "tag_color", "tag_class"]
        read_only_fields = ["id"]
        validators = []


class JournalTagsSerializer(serializers.ModelSerializer):
    """
    Serializer for listing the Journal's Tags
    """

    class Meta:
        model = Tags
        fields = ["id", "tag_name", "tag_color", "tag_class"]
        read_only_fields = ["id"]


class JournalJournalTableSerializer(serializers.ModelSerializer):
    """
    Serializer for listing Journal's Journal Tables
    """

    class Meta:
        model = JournalTables
        #  "journal",
        fields = ["id", "table_name"]
        read_only_fields = ["id"]


class JournalSerializer(serializers.ModelSerializer):
    """
    Serializer for Journal
    """

    journal_tables = JournalJournalTableSerializer(many=True, required=False)
    tags = JournalTagsSerializer(many=True, source="user.tags", required=False)
    username = serializers.CharField(source="user.username", required=False)

    class Meta:
        model = Journal
        fields = [
            "id",
            "journal_name",
            "journal_description",
            "journal_tables",
            "current_table",
            "journal_table_func",
            "username",
            "tags",
        ]
        read_only_fields = ["id", "journal_tables"]
        default_table_model = JournalTables

    def create_copy_default_tags_for_user(self):
        """
        copy the admin default tags to the user on journal creation
        """
        request_user = (
            self.context["request"].user
            if self.context["request"].user.is_authenticated
            else self.context["user"]
        )

        tags = Tags.objects.filter(tag_user__is_superuser=True).values(
            "tag_name", "tag_color", "tag_class"
        )
        copied_tags = copy.deepcopy(tags)
        tags_list = []
        for i in copied_tags:
            i["tag_user"] = request_user
            tags_list.append(Tags(**i))

        try:
            Tags.objects.bulk_create(tags_list)
        except IntegrityError as e:
            raise serializers.ValidationError(detail=e)

    def create_default_journal_tables_for_journal(self, journal):
        default_tables_list = [
            self.Meta.default_table_model(**default_table)
            for default_table in get_table_defaults(journal)
        ]

        try:
            self.Meta.default_table_model.objects.bulk_create(default_tables_list)
        except IntegrityError as e:
            raise serializers.ValidationError(detail=e)
        return default_tables_list

    def create(self, validated_data):
        """
        Create a Journal
        """

        request_user = validated_data.get("user", None)

        if request_user is None:
            validated_data["user"] = self.context["user"]

        journal = Journal.objects.create(**validated_data)
        self.create_copy_default_tags_for_user()
        default_tables = self.create_default_journal_tables_for_journal(journal)

        # add initial cur table
        journal.current_table = default_tables[0].id
        journal.save()
        return journal

    def update_current_table(self, instance, attr, value):
        print("the attr val", attr, value)
        if attr == "current_table":
            get_table = JournalTables.objects.filter(id=int(value)).count()
            if get_table == 0:
                set_default_cur_table = JournalTables.objects.filter(
                    journal__id=instance.id
                )
                if set_default_cur_table.count() > 0:
                    table_to_set = set_default_cur_table.first()
                    instance.current_table = table_to_set.id
                    return True
                else:
                    instance.current_table = None
                    return True

            instance.current_table = int(value)
            return True
        return False

    def update(self, instance, validated_data):
        """
        Update a Journal
        """
        try:
            print("the validated data", validated_data)
            for attr, value in validated_data.items():
                updated_cur_table = self.update_current_table(instance, attr, value)
                if updated_cur_table == False:
                    print("the not update cur table", attr, value)
                    setattr(instance, attr, value)

            instance.save()
            return instance
        except Exception as e:
            raise exceptions.ValidationError(detail=e)


class BaseSubModelsSerializer(serializers.ModelSerializer):
    """
    Base submodel serializer for other submodel serializers to inherit
    """

    def create(self, validated_data):
        activity = validated_data.pop("activity", None)
        model_obj = self.Meta.model.objects.create(**validated_data)

        if activity is not None:
            model_obj.activity = activity

        model_obj.save()

        return model_obj

    def update(self, instance, validated_data):
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class IntentionsSerializer(BaseSubModelsSerializer):
    class Meta:
        model = Intentions
        fields = ["id", "intention", "activity", "ordering"]
        read_only_fields = ["id"]


class HappeningsSerializer(BaseSubModelsSerializer):
    class Meta:
        model = Happenings
        fields = ["id", "happening", "activity", "ordering"]
        read_only_fields = ["id"]


class GratefulForSerializer(BaseSubModelsSerializer):
    class Meta:
        model = GratefulFor
        fields = ["id", "grateful_for", "activity", "ordering"]
        read_only_fields = ["id"]


class ActionItemsSerializer(BaseSubModelsSerializer):
    class Meta:
        model = ActionItems
        fields = ["id", "action_item", "activity", "checked", "ordering"]
        read_only_fields = ["id"]


class ActivitiesTagsSerializer(serializers.ModelSerializer):
    """
    Serializer for returning the tags linked to an activity
    """

    class Meta:
        model = Tags
        fields = ["id", "tag_color", "tag_name", "tag_class"]


class ActivitiesSerializer(
    ListSerializerClassInitMixin, SubmodelMixin, serializers.ModelSerializer
):
    """
    Serializer for serializing the Activities
    """

    tags = ActivitiesTagsSerializer(many=True, required=False)
    intentions = IntentionsSerializer(many=True, required=False)
    happenings = HappeningsSerializer(many=True, required=False)
    grateful_for = GratefulForSerializer(many=True, required=False)
    action_items = ActionItemsSerializer(many=True, required=False)

    def to_internal_value(self, data):
        if (
            self.context["request"].method in ["POST", "PUT", "PATCH"]
            and self.context.get("batch_duplicate_activities", None) is None
        ):
            copied_data = data.copy()
            try:
                tags = copied_data.pop("tags", None)
            except AttributeError as e:
                tags = copied_data.pop("tags", None)

            if tags is not None:
                if tags is not None and not isinstance(tags, list):
                    raise exceptions.ValidationError(
                        "A list is expected for the tags field"
                    )

                ret = super().to_internal_value(copied_data)
                ret["tags"] = tags
                return ret
            # ret = super().to_internal_value(data)
            # return ret
            if isinstance(data, QueryDict):
                ret = super().to_internal_value(data)
                return ret

            return data

        ret = super().to_internal_value(data)
        return ret

    def create_default_submodels(self, model):
        # create default submodels
        for submodel in SUBMODELS_LIST:
            submodel_payload = {
                "activity": model,
                self.get_submodel_field(submodel): "",
            }

            self.get_submodel(submodel).objects.create(**submodel_payload)

    def update_action_items_checked(self, submodel):
        try:
            if submodel is not None and submodel["update_checked"]:
                action_item_submodel = self.get_submodel(submodel["type"]).objects.get(
                    id=submodel["id"]
                )
                action_item_submodel.checked = submodel["checked"]
                action_item_submodel.save()
                return action_item_submodel
            return submodel
        except Exception as e:
            raise serializers.ValidationError(detail=e)

    def update_model_ordering(self, ordering_payload, model):
        instance_ids = list(map(lambda x: x["id"], ordering_payload))
        instance_orderings = list(map(lambda x: x["ordering"], ordering_payload))
        instances = model.objects.filter(id__in=instance_ids)

        instances_update_list = []
        for i, instance in enumerate(instances):
            instance.ordering = instance_orderings[i]
            instances_update_list.append(instance)
        try:
            model.objects.bulk_update(instances_update_list, ["ordering"])
            return instances_update_list
        except IntegrityError as e:
            raise serializers.ValidationError(detail=e)

    def create(self, validated_data):
        try:
            tags = validated_data.pop("tags", [])
            activities_ordering_list = validated_data.pop("ordering_list", None)
            journal_table_data = validated_data.pop("journal_table", None)
            journal_table = (
                JournalTables.objects.get(id=journal_table_data)
                if isinstance(journal_table_data, int)
                else journal_table_data
            )

            create_payload = {
                "name": validated_data["name"],
                "journal_table": journal_table,
            }
            if activities_ordering_list is not None:
                # add the create item ordering if its a relative item being added
                create_payload["ordering"] = activities_ordering_list[
                    "create_item_ordering"
                ]

            activity = Activities.objects.create(**create_payload)
            print("the created activity value", activity)

            if len(tags) > 0:
                for tagId in tags:
                    tag = Tags.objects.get(id=int(tagId))
                    activity.tags.add(tag)

            if activities_ordering_list is not None:
                ordering_list = activities_ordering_list["table_items_ordering"]
                self.update_model_ordering(ordering_list, self.Meta.model)

            self.create_default_submodels(activity)


            return activity
        except Exception as e:
            raise exceptions.ValidationError(detail=e)

    def update(self, instance, validated_data):
        try:
            submodels_list = SUBMODELS_LIST
            submodels_validated_data = {}
            tags = validated_data.pop("tags", None)

            for submodels_data in submodels_list:
                submodels_validated_data[submodels_data] = validated_data.pop(
                    submodels_data, None
                )

            for attr, value in validated_data.items():
                setattr(instance, attr, value)

            if tags is not None:  # len(tags) > 0:
                instance.tags.clear()
                for tagId in tags:
                    tag = Tags.objects.get(id=tagId)
                    instance.tags.add(tag)

                    # tag = Tags.objects.filter(id=tagId)
                    # if tag.exists():
                    # instance.tags.add(tag[0])

            for attr, value in submodels_validated_data.items():
                if value is not None:
                    create_submodel_payload = value.get("create", None)
                    update_submodel_payload = value.get("update", None)
                    ordering_submodel_payload = value.get("ordering_list", None)
                    update_only = value.get("update_only", None) is not None
                    update_and_create = value.get("update_and_create", None)

                    if update_only:
                        # update submodel
                        self.update_sub_model(
                            value.get("type", None),
                            update_submodel_payload,
                            update_submodel_payload["id"],
                            instance,
                        )
                    if update_and_create:
                        self.create_sub_model(
                            submodel_type=value.get("type", None),
                            model_instance=instance,
                            submodel_data=create_submodel_payload,
                        )

                        self.update_sub_model(
                            submodel_type=value.get("type", None),
                            submodel_data=update_submodel_payload,
                            submodel_id=update_submodel_payload["id"],
                            activity_instance=instance,
                        )
                    if (
                        ordering_submodel_payload is not None
                        and len(ordering_submodel_payload) > 0
                    ):
                        self.update_model_ordering(
                            ordering_submodel_payload,
                            self.get_submodel(value.get("type", None)),
                        )

            # TODO: add relativeItem/prop for ordering
            if submodels_validated_data.get("action_items", None) is not None:
                self.update_action_items_checked(
                    submodels_validated_data["action_items"].get(
                        "update_action_item_checked", None
                    )
                )

            instance.save()
            return instance
        except Exception as e:
            raise exceptions.ValidationError(detail=e)

    class Meta:
        list_serializer_class = BatchUpdateActivitiesSerializer
        model = Activities
        fields = [
            "id",
            "name",
            "tags",
            "journal_table",
            "intentions",
            "happenings",
            "grateful_for",
            "action_items",
            "ordering",
            "created",
        ]
        read_only_fields = ["id"]


class JournalTableActivitiesSerializer(serializers.ModelSerializer):
    """
    Serializer for serializing the Activities
    """

    tags = ActivitiesTagsSerializer(many=True, required=False)
    intentions = IntentionsSerializer(many=True, required=False)
    happenings = HappeningsSerializer(many=True, required=False)
    grateful_for = GratefulForSerializer(many=True, required=False)
    action_items = ActionItemsSerializer(many=True, required=False)

    class Meta:
        model = Activities
        fields = [
            "id",
            "name",
            "tags",
            "journal_table",
            "intentions",
            "happenings",
            "grateful_for",
            "action_items",
            "created"
        ]
        read_only_fields = ["id"]


class JournalTableSerializer(CloneModelMixin, serializers.ModelSerializer):
    """
    Serializer for Journal Table
    """

    activities = JournalTableActivitiesSerializer(many=True, required=False)

    def to_internal_value(self, data):
        try:
            if not isinstance(data, dict):
                raise exceptions.ValidationError(
                    "A list is expected for the tags field"
                )
            duplicate = data.get("duplicate", None)
            journal_table = data.get("journal_table", None)

            ret = super().to_internal_value(data)
            ret["duplicate"] = duplicate
            ret["journal_table"] = journal_table
            return ret
        except Exception as e:
            raise serializers.ValidationError(detail=e)

    class Meta:
        model = JournalTables
        #  "journal",
        fields = ["id", "table_name", "activities"]
        optional_fields = [
            "table_name",
        ]
        read_only_fields = ["id", "activities"]

    def create_clone_table_name(self, table_name, name_count):
        return f"{table_name} ({name_count})"

    def create(self, validated_data):
        """
        Create a Journal Table
        """
        journal = validated_data.pop("journal", None)
        duplicate_table = validated_data.pop("duplicate", None)

        journal = (
            Journal.objects.get(id=journal) if isinstance(journal, int) else journal
        )

        if duplicate_table is None:
            journal_table_payload = {"journal": journal}
            journal_table_name = validated_data.get("table_name", None)
            if journal_table_name is not None:
                journal_table_payload["table_name"] = journal_table_name
            journal_table = JournalTables.objects.create(**journal_table_payload)

        if duplicate_table is not None:
            journal_table_to_duplicate_id = validated_data.pop("journal_table", None)

            if journal_table_to_duplicate_id is not None:
                journal_table_to_duplicate = JournalTables.objects.get(
                    id=journal_table_to_duplicate_id
                )

                journal_table_with_similar_name_count = JournalTables.objects.filter(
                    table_name__startswith=journal_table_to_duplicate.table_name
                ).count()
                clone_table_name = self.create_clone_table_name(
                    journal_table_to_duplicate.table_name,
                    journal_table_with_similar_name_count,
                )

                clone_table = self.duplicate_model(journal_table_to_duplicate)
                clone_table.table_name = clone_table_name
                clone_table.save()

                return clone_table

        return journal_table

    def update(self, instance, validated_data):
        """
        Update a Journal
        """
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance
