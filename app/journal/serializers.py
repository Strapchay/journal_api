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
)

from django.db.models import Q
from django.db import IntegrityError
from django.http import QueryDict
import copy
from journal.config import get_table_defaults, SUBMODELS_LIST
import copy
from collections import OrderedDict


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


class BatchDuplicateActivitiesSerializer(
    BatchDuplicateActivitiesSerializerMixin,
    serializers.ListSerializer,
):
    """
    Serializer for Activities for duplicating batch activities
    """

    def duplicate_model(self, instance, callback=None):
        related_objects_to_copy = []
        relations_to_set = {}

        for field in instance._meta.get_fields():
            if field.name == "id":
                pass
            elif field.one_to_many:
                related_object_manager = getattr(instance, field.get_accessor_name())
                related_objects = list(related_object_manager.all())

                if related_objects:
                    related_objects_to_copy += related_objects

            elif field.many_to_many and hasattr(field, "field"):  # not
                related_object_manager = getattr(instance, field.name)

                relations = list(related_object_manager.all())
                if relations:
                    relations_to_set[field.name] = relations
            else:
                pass

        instance.pk = None

        if callback and callable(callback):
            instance = callback(instance)

        instance.save()

        for related_object in related_objects_to_copy:
            for related_object_field in related_object._meta.fields:
                if related_object_field.related_model == instance.__class__:
                    setattr(related_object, related_object_field.name, instance)
                    new_related_object = self.duplicate_model(related_object)
                    new_related_object.save()

        for field_name, relations in relations_to_set.items():
            field = getattr(instance, field_name)
            field.set(relations)
            text_relations = []
            for relation in relations:
                text_relations.append(str(relation))
        return instance

    def create(self, validated_data):
        """
        Create Duplicated Activities Items
        """
        activities_to_duplicate = Activities.objects.filter(
            id__in=validated_data[0]["ids"]
        )
        duplicates_to_create = [
            self.duplicate_model(activity) for activity in activities_to_duplicate
        ]

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
    }

    def __init__(self, *args, **kwargs) -> None:
        list_serializer_type = kwargs.pop("type", None)

        super().__init__(*args, **kwargs)

        if list_serializer_type is not None:
            print("the list seriatype", list_serializer_type)
            self.Meta.list_serializer_class = self.list_serializer_type_classes[
                list_serializer_type
            ]


class TagsSerializer(serializers.ModelSerializer):
    """
    Serializer for serializing the Tags
    """

    def format_tag_name(self, attrs):
        return attrs["tag_name"][0].upper() + attrs["tag_name"][1:].lower()

    def validate_tag_matches_color_and_class(self, tag_color, tag_class):
        """
        Validates that the tag color and class are relative
        """
        if tag_color is not None and tag_class is not None:
            split_color = tag_color.split(" ")
            color = (
                split_color[1].lower()
                if len(split_color) > 1
                else split_color[0].lower()
            )

            if color in tag_class:
                return True
            else:
                raise exceptions.ValidationError(
                    detail="The tag_color and tag_class has to be relative to each other"
                )

        raise exceptions.ValidationError(
            detail="The tag_color and tag_class cannot be empty"
        )

    def validate(self, attrs):
        try:
            tag_model_filter = self.Meta.model.objects.filter(
                tag_user=self.context["request"].user
            ).values_list("tag_name", flat=True)

            formatted_tag_name = self.format_tag_name(attrs)

            if self.context["view"].action == "create":
                if formatted_tag_name in tag_model_filter:
                    raise exceptions.ValidationError(
                        detail="Cannot Create Existing Tag"
                    )

            if attrs["tag_color"] is None or attrs["tag_class"] is None:
                raise exceptions.ValidationError(
                    detail="The tag_color and tag_class has to be supplied"
                )

            self.validate_tag_matches_color_and_class(
                attrs["tag_color"], attrs["tag_class"]
            )

            # check if the value gets assigned to the field
            attrs["tag_name"] = formatted_tag_name

            super().validate(attrs)

            return attrs
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

    class Meta:
        model = Journal
        fields = [
            "id",
            "journal_name",
            "journal_description",
            "journal_tables",
            "current_table",
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
        for attr, value in validated_data.items():
            updated_cur_table = self.update_current_table(instance, attr, value)
            if updated_cur_table == False:
                setattr(instance, attr, value)

        instance.save()
        return instance


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


class ActivitiesSerializer(ListSerializerClassInitMixin, serializers.ModelSerializer):
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

    def get_submodel_field(self, submodel_type):
        if submodel_type == "grateful_for":
            return submodel_type
        return submodel_type[:-1]

    def get_submodel(self, submodel_type):
        return {
            "intentions": Intentions,
            "happenings": Happenings,
            "action_items": ActionItems,
            "grateful_for": GratefulFor,
        }.get(submodel_type)

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
            print("check excp", e)

    def create_sub_model(self, submodel_type, model_instance, submodel_data):
        try:
            submodel_field = self.get_submodel_field(submodel_type)
            submodel_field_value = submodel_data[submodel_field]

            submodel_payload = {
                submodel_field: submodel_field_value,
                "activity": model_instance,
            }
            if submodel_data.get("relative_item") is not None:
                submodel_payload["ordering"] = submodel_data["ordering"]
            submodel_obj = self.get_submodel(submodel_type).objects.create(
                **submodel_payload
            )
            return submodel_obj

        except Exception as e:
            print("except create trig", e)

    def update_sub_model(
        self, submodel_type, submodel_data, submodel_id, activity_instance
    ):
        try:
            if submodel_id is not None:
                submodel_instance = self.get_submodel(submodel_type).objects.get(
                    id=submodel_id
                )
                submodel_field = self.get_submodel_field(submodel_type)

                print("the submodel datat to update wth", submodel_data)
                # set the submodel value on the submodel
                setattr(
                    submodel_instance, submodel_field, submodel_data[submodel_field]
                )
                submodel_instance.save()
            else:
                self.create_sub_model(
                    submodel_type=submodel_type,
                    model_instance=activity_instance,
                    submodel_data=submodel_data,
                )
        except Exception as e:
            print("except trig", e)

    def update_submodel_ordering(self, model_type, ordering_payload):
        submodel_type = model_type.get("type", None)
        submodel_ids = list(map(lambda x: x["id"], ordering_payload))
        submodel_orderings = list(map(lambda x: x["ordering"], ordering_payload))

        submodel_model = self.get_submodel(submodel_type)
        submodel_instances = submodel_model.objects.filter(id__in=submodel_ids)
        print("submod insts", submodel_instances)
        submodels_update_list = []
        for i, submodel in enumerate(submodel_instances):
            submodel.ordering = submodel_orderings[i]
            submodels_update_list.append(submodel)
        try:
            submodel_model.objects.bulk_update(submodels_update_list, ["ordering"])
            return submodels_update_list
        except IntegrityError as e:
            raise serializers.ValidationError(detail=e)

    def create(self, validated_data):
        try:
            tags = validated_data.pop("tags", [])

            journal_table_data = validated_data.pop("journal_table", None)
            journal_table = (
                JournalTables.objects.get(id=journal_table_data)
                if isinstance(journal_table_data, int)
                else journal_table_data
            )
            print("journal table", journal_table)
            print("val data", validated_data)
            activity = Activities.objects.create(
                name=validated_data["name"], journal_table=journal_table
            )
            print("the activity", activity)

            if len(tags) > 0:
                for tagId in tags:
                    tag = Tags.objects.get(id=int(tagId))
                    activity.tags.add(tag)

            self.create_default_submodels(activity)

            return activity
        except Exception as e:
            print("triggered activ create", e)
            raise exceptions.ValidationError(detail=e)

    def update(self, instance, validated_data):
        try:
            # TODO: add the ordering list for thee activities update itself
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
                        self.update_submodel_ordering(value, ordering_submodel_payload)

            # TODO: add relativeItem/prop for ordering
            if submodels_validated_data.get("action_items", None) is not None:
                self.update_action_items_checked(
                    submodels_validated_data["action_items"].get(
                        "update_action_item_checked", None
                    )
                )

            instance.save()
            print(instance)
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
        ]
        read_only_fields = ["id"]


class JournalTableSerializer(serializers.ModelSerializer):
    """
    Serializer for Journal Table
    """

    activities = JournalTableActivitiesSerializer(many=True, required=False)

    class Meta:
        model = JournalTables
        #  "journal",
        fields = ["id", "table_name", "activities"]
        read_only_fields = ["id", "activities"]

    def create(self, validated_data):
        """
        Create a Journal Table
        """
        journal = validated_data.pop("journal", None)
        journal_table = JournalTables.objects.create(
            table_name=validated_data["table_name"], journal=journal
        )

        return journal_table

    def update(self, instance, validated_data):
        """
        Update a Journal
        """
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance
