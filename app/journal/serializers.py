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
)
from django.db.models import Q
from django.db import IntegrityError
import copy


class JournalSerializer(serializers.ModelSerializer):
    """
    Serializer for Journal
    """

    class Meta:
        model = Journal
        fields = ["id", "journal_name", "journal_description"]
        read_only_fields = ["id"]

    def create_copy_default_tags_for_user(self):
        """
        copy the admin default tags to the user on journal creation
        """
        request_user = self.context["request"].user

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

    def create(self, validated_data):
        """
        Create a Journal
        """
        journal = Journal.objects.create(**validated_data)
        self.create_copy_default_tags_for_user()
        return journal

    def update(self, instance, validated_data):
        """
        Update a Journal
        """
        for attr, value in validated_data.items():
            setattr(instance, attr, value)

        instance.save()
        return instance


class JournalTableSerializer(serializers.ModelSerializer):
    """
    Serializer for Journal Table
    """

    class Meta:
        model = JournalTables
        fields = ["id", "table_name"]
        read_only_fields = ["id"]

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


class TagsSerializer(serializers.ModelSerializer):
    """
    Serializer for serializing the Tags
    """

    def format_tag_name(self, attrs):
        return attrs["tag_name"][0].upper() + attrs["tag_name"][1:].lower()

    def validate(self, attrs):
        tag_model_filter = self.Meta.model.objects.filter(
            tag_user=self.context["request"].user
        ).values_list("tag_name", flat=True)

        formatted_tag_name = self.format_tag_name(attrs)

        if formatted_tag_name in tag_model_filter:
            raise exceptions.ValidationError(detail="Cannot Create Existing Tag")

        # check if the value gets assigned to the field
        attrs["tag_name"] = formatted_tag_name

        # return attrs

        super().validate(attrs)

        return attrs

    def create(self, validated_data):
        user = validated_data.pop("tag_user", None)
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

    def to_internal_value(self, data):
        if self.context["request"].method == "POST":
            tags = data.getlist("tags", None)

            if tags is not None:
                if tags is not None and not isinstance(tags, list):
                    raise exceptions.ValidationError(
                        "A list is expected for the tags field"
                    )
                ret = super().to_internal_value(data)
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
            print("encountered", e)

    def update(self, instance, validated_data):
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

    class Meta:
        model = Activities
        fields = ["id", "name", "tags", "journal_table"]
        read_only_fields = ["id"]
