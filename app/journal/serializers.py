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
from django.db.models import Q
from django.db import IntegrityError
import copy
from journal.config import get_table_defaults


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

    class Meta:
        model = Journal
        fields = [
            "id",
            "journal_name",
            "journal_description",
            "journal_tables",
            "current_table",
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
        print("the journal", journal.current_table)
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
        tag_model_filter = self.Meta.model.objects.filter(
            tag_user=self.context["request"].user
        ).values_list("tag_name", flat=True)

        formatted_tag_name = self.format_tag_name(attrs)

        if formatted_tag_name in tag_model_filter:
            raise exceptions.ValidationError(detail="Cannot Create Existing Tag")

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
        fields = ["id", "intention", "activity"]
        read_only_fields = ["id"]


class HappeningsSerializer(BaseSubModelsSerializer):
    class Meta:
        model = Happenings
        fields = ["id", "happening", "activity"]
        read_only_fields = ["id"]


class GratefulForSerializer(BaseSubModelsSerializer):
    class Meta:
        model = GratefulFor
        fields = ["id", "grateful_for", "activity"]
        read_only_fields = ["id"]


class ActionItemsSerializer(BaseSubModelsSerializer):
    class Meta:
        model = ActionItems
        fields = ["id", "action_item", "activity"]
        read_only_fields = ["id"]


class ActivitiesTagsSerializer(serializers.ModelSerializer):
    """
    Serializer for returning the tags linked to an activity
    """

    class Meta:
        model = Tags
        fields = ["id", "tag_color", "tag_name", "tag_class"]


class ActivitiesSerializer(serializers.ModelSerializer):
    """
    Serializer for serializing the Activities
    """

    tags = ActivitiesTagsSerializer(many=True, required=False)
    intentions = IntentionsSerializer(many=True, required=False)
    happenings = HappeningsSerializer(many=True, required=False)
    grateful_for = GratefulForSerializer(many=True, required=False)
    action_items = ActionItemsSerializer(many=True, required=False)

    def to_internal_value(self, data):
        if self.context["request"].method in ["POST", "PUT", "PATCH"]:
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

        ret = super().to_internal_value(data)
        return ret

    def create(self, validated_data):
        try:
            tags = validated_data.pop("tags", [])

            journal_table = validated_data.pop("journal_table", None)

            activity = Activities.objects.create(
                name=validated_data["name"], journal_table=journal_table
            )

            if len(tags) > 0:
                for tagId in tags:
                    tag = Tags.objects.get(id=int(tagId))
                    activity.tags.add(tag)
            return activity
        except Exception as e:
            raise exceptions.ValidationError(detail=e)

    def update(self, instance, validated_data):
        try:
            tags = validated_data.pop("tags", [])

            for attr, value in validated_data.items():
                setattr(instance, attr, value)

            if len(tags) > 0:
                instance.tags.clear()
                for tagId in tags:
                    tag = Tags.objects.get(id=tagId)
                    instance.tags.add(tag)
            instance.save()
            return instance
        except Exception as e:
            raise exceptions.ValidationError(detail=e)

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
