from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import exceptions
from rest_framework.exceptions import ValidationError
from rest_framework import status
from core.models import Intentions, GratefulFor, Happenings, ActionItems


class BatchSerializerMixin:
    """
    Mixin to be subclassed by all batch related serializer mixins
    """

    def to_internal_value(self, data):
        list_instance_exists_in_context = False
        list_instances = ["batch_duplicate_activities", "batch_tag_processor"]
        action_context = self.context.keys()

        for i in list_instances:
            if i in action_context:
                list_instance_exists_in_context = True

        if not list_instance_exists_in_context and not isinstance(data, dict):
            raise ValidationError("Invalid Data Supplied, a Dict is expected")

        if list_instance_exists_in_context and not isinstance(data, list):
            raise ValidationError("Invalid Data Supplied, a List is expected")

        if self.passes_test():
            return data
        raise ValidationError("Could not validate request data")


class BatchUpdateActivitiesSerializerMixin(BatchSerializerMixin):
    """
    Mixin to be used with updating multiple activities
    """

    def passes_test(self):
        test = self.context["request"].method == "PATCH"
        test &= self.context.get("batch_update_activities", False)
        return test


class BatchTagSerializerMixin(BatchSerializerMixin):
    """
    Mixin to be used for CRUD with multiple activities"""

    def passes_test(self):
        test = (
            True
            if self.context["request"].method in ["PATCH", "DELETE", "POST"]
            else False
        )
        test &= self.context.get("batch_tag_processor", False)
        return test


class BatchSubmodelSerializerMixin(BatchSerializerMixin):
    """
    Mixin to be used for CRUD with multiple submodels"""

    def passes_test(self):
        test = (
            True
            if self.context["request"].method in ["PATCH", "DELETE", "POST"]
            else False
        )
        test &= self.context.get("batch_submodel_processor", False)
        return test


class BatchDeleteActivitiesSerializerMixin(BatchSerializerMixin):
    """
    Mixin to be used with updating multiple activities
    """

    def passes_test(self):
        test = self.context["request"].method == "DELETE"
        test &= self.context.get("batch_delete_activities", False)
        return test


class BatchDuplicateActivitiesSerializerMixin(BatchSerializerMixin):
    """
    Mixin to be used with duplicating multiple activities
    """

    def passes_test(self):
        test = self.context["request"].method == "POST"
        test &= self.context.get("batch_duplicate_activities", False)
        return test


class BatchRouteMixin:
    """
    Mixin to be subclassed by all batch route related mixins
    """

    def get_object(self):
        lookup_url_kwargs = self.lookup_url_kwarg or self.lookup_field

        if lookup_url_kwargs in self.kwargs:
            return super().get_object()
        return

    def get_serializer(self, *args, **kwargs):
        return super().get_serializer(*args, **kwargs)

    def get_serializer_context(self):
        context = super().get_serializer_context()
        if self.action in [
            "batch_update_activities",
            "batch_duplicate_activities",
            "batch_delete_activities",
            "batch_tag_processor",
            "batch_submodel_processor",
        ]:
            context[self.action] = True
        return context

    def validate_ids(self, data, field="id", unique=True):
        if isinstance(data, list):
            id_list = [int(i) for i in data]
            if unique and len(id_list) != len(set(id_list)):
                raise ValidationError(
                    "Cannot make multiple request operation on a single instance"
                )

            return id_list
        return [data]

    def validate_tag_ids(self, data, unique=True, field=False):
        if isinstance(data, list):
            tag_list = [int(i["id"]) for i in data] if field else [int(i) for i in data]
            if unique and len(tag_list) != len(set(tag_list)):
                raise ValidationError(
                    "Cannot make multiple request operation on a single instance"
                )

            return tag_list
        return [data]


class TagsValidatorMixin:
    def format_tag_name(self, attrs, skip=False):
        if attrs["tag_name"] is None:
            if not skip:
                raise exceptions.ValidationError(detail="The tag_name was not provided")

            if skip:
                return None

        return attrs["tag_name"][0].upper() + attrs["tag_name"][1:].lower()

    def validate_tag_matches_color_and_class(self, tag_color, tag_class, skip=False):
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
                if not skip:
                    raise exceptions.ValidationError(
                        detail="The tag_color and tag_class has to be relative to each other"
                    )
                if skip:
                    return None
        if not skip:
            raise exceptions.ValidationError(
                detail="The tag_color and tag_class cannot be empty"
            )
        if skip:
            return None

    def validate_tag_class_and_color_has_value(self, tag_class, tag_color, skip=False):
        if tag_class is None or tag_color is None:
            if not skip:
                raise exceptions.ValidationError(
                    detail="The tag_color and tag_class has to be supplied"
                )
            if skip:
                return None
        return True

    def validate_for_single_tag(self, attrs):
        tag_model_filter = self.Meta.model.objects.filter(
            tag_user=self.context["request"].user
        ).values_list("tag_name", flat=True)

        if self.context["view"].action == "create":
            formatted_tag_name = self.format_tag_name(attrs)
            if formatted_tag_name in tag_model_filter:
                raise exceptions.ValidationError(detail="Cannot Create Existing Tag")
            attrs["tag_name"] = formatted_tag_name

        self.validate_tag_class_and_color_has_value(
            attrs["tag_color"], attrs["tag_class"]
        )
        self.validate_tag_matches_color_and_class(
            attrs["tag_color"], attrs["tag_class"]
        )
        # check if the value gets assigned to the field
        super().validate(attrs)
        return attrs

    def validate_for_multiple_tags(self, tag_list):
        valid_tags_list = []
        tag_model_filter = self.child.Meta.model.objects.filter(
            tag_user=self.context["request"].user
        ).values_list("tag_name", flat=True)

        for attrs in tag_list:
            formatted_tag_name = self.format_tag_name(attrs, True)
            if formatted_tag_name is None:
                continue
            if self.context["view"].action == "create":
                if formatted_tag_name in tag_model_filter:
                    continue

            validate_value = self.validate_tag_class_and_color_has_value(
                attrs["tag_color"], attrs["tag_class"]
            )
            if validate_value is not None:
                validate_meta = self.validate_tag_matches_color_and_class(
                    attrs["tag_color"], attrs["tag_class"]
                )
                if validate_meta is not None:
                    attrs["tag_name"] = formatted_tag_name
                    # check if the value gets assigned to the field
                    valid_tags_list.append(attrs)
        return valid_tags_list


class SubmodelMixin:
    """
    Mixin for implementing CRUD functionalities on a submodl
    """

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
            raise ValidationError(e)

    def update_sub_model(
        self, submodel_type, submodel_data, submodel_id, activity_instance
    ):
        try:
            if submodel_id is not None:
                submodel_instance = self.get_submodel(submodel_type).objects.get(
                    id=submodel_id
                )
                submodel_field = self.get_submodel_field(submodel_type)

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
            raise ValidationError(e)


class BatchTagRouteMixin:
    """
    Mixin that adds a `batch_tag` API route to a viewset.To be used with BatchTagSerializerMixin
    """

    # TODO: add endpoint compatbility for mixin
    @action(
        detail=False,
        methods=["PATCH", "POST", "DELETE"],
        url_name="batch_tag_processor",
    )
    def batch_tag_processor(self, request, *args, **kwargs):
        try:
            ids = None
            instance_methods = ["PATCH", "DELETE"]
            request_method = self.request.method
            if request_method in instance_methods:
                ids = self.validate_tag_ids(
                    request.data["tags_list"],
                    True,
                    True if request_method != "DELETE" else False,
                )

            if request_method == "POST":
                queryset = self.get_object()

            if request_method in instance_methods:
                queryset = self.filter_queryset(self.get_queryset(ids=ids))
            # delete the queryset if DEL req
            if request_method == "DELETE":
                queryset.delete()
                return Response(
                    self.serializer_class(queryset, many=True).data,
                    status=status.HTTP_204_NO_CONTENT,
                )

            serializer = self.get_serializer(
                queryset,
                data=request.data["tags_list"],
                partial=True if request_method == "PATCH" else False,
                many=True,
            )

            serializer.is_valid(raise_exception=True)

            if request_method == "PATCH":
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            if request.method == "POST":
                self.perform_create(serializer)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            raise ValidationError(e)


class BatchSubmodelRouteMixin:
    """
    Mixin that adds a `batch_tag` API route to a viewset.To be used with BatchTagSerializerMixin
    """

    @action(
        detail=False,
        methods=["PATCH", "POST", "DELETE"],
        url_name="batch_submodel_processor",
    )
    def batch_submodel_processor(self, request, *args, **kwargs):
        try:
            ids = None
            instance_methods = ["PATCH", "DELETE"]
            request_method = self.request.method
            if request_method in instance_methods:
                ids = self.validate_tag_ids(
                    request.data["tags_list"],
                    True,
                    True if request_method != "DELETE" else False,
                )

            if request_method == "POST":
                queryset = self.get_object()

            if request_method in instance_methods:
                queryset = self.filter_queryset(self.get_queryset(ids=ids))

            # delete the queryset if DEL req
            if request_method == "DELETE":
                queryset.delete()
                return Response(
                    self.serializer_class(queryset, many=True).data,
                    status=status.HTTP_204_NO_CONTENT,
                )

            serializer = self.get_serializer(
                queryset,
                data=request.data["tags_list"],
                partial=True if request_method == "PATCH" else False,
                many=True,
            )
            serializer.is_valid(raise_exception=True)

            if request_method == "PATCH":
                self.perform_update(serializer)
                return Response(serializer.data, status=status.HTTP_200_OK)
            if request.method == "POST":
                self.perform_create(serializer)
                return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            raise ValidationError(e)


class BatchUpdateActivitiesRouteMixin:
    """
    Mixin that adds a `batch_update_activities` API route to a viewset. To be used with BatchUpdateActivitiesSerializerMixin
    """

    @action(detail=False, methods=["PATCH"], url_name="batch_update_activities")
    def batch_update_activities(self, request, *args, **kwargs):
        try:
            ids = self.validate_ids(request.data["activities_list"][0]["ids"])
            val_tags = self.validate_tag_ids(request.data["activities_list"][0]["tags"])

            queryset = self.filter_queryset(self.get_queryset(ids=ids))

            serializer = self.get_serializer(
                queryset,
                data=request.data["activities_list"],
                partial=True,
                many=True,
                type=self.action,
            )
            serializer.is_valid(raise_exception=True)

            self.perform_update(serializer)
            return Response(serializer.data, status=status.HTTP_200_OK)

        except Exception as e:
            raise ValidationError(e)


class BatchDeleteActivitiesRouteMixin:
    """
    Mixin that adds a `batch_update_activities` API route to a viewset. To be used with BatchUpdateActivitiesSerializerMixin
    """

    @action(detail=False, methods=["DELETE"], url_name="batch_delete_activities")
    def batch_delete_activities(self, request, *args, **kwargs):
        try:
            ids = self.validate_ids(request.data["delete_list"])

            queryset = self.filter_queryset(self.get_queryset(ids=ids))
            queryset.delete()
            return Response(
                self.serializer_class(queryset, many=True).data,
                status=status.HTTP_204_NO_CONTENT,
            )

        except Exception as e:
            raise ValidationError(e)


class BatchDuplicateActivitiesRouteMixin:
    """
    Mixin that adds a `batch_duplicate_activities` API route to a viewset. To be used with BatchDuplicateActivitiesSerializerMixin
    """

    @action(detail=False, methods=["POST"], url_name="batch_duplicate_activities")
    def batch_duplicate_activities(self, request, *args, **kwargs):
        try:
            ids = self.validate_ids(request.data["duplicate_list"][0]["ids"])
            queryset = self.get_object()

            serializer = self.get_serializer(
                queryset,
                data=request.data["duplicate_list"],
                partial=True,
                many=True,
                type=self.action,
            )

            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        except Exception as e:
            raise ValidationError(e)


class CloneModelMixin:
    def duplicate_model(self, instance, callback=None, create_instance=None):
        related_objects_to_copy = []
        relations_to_set = {}

        for field in instance._meta.get_fields():
            if field.name == "id" or field.name == "ordering":
                continue

            elif (
                field.name == "ordering" and instance.__class__.__name__ == "Activities"
            ):
                continue

            elif field.one_to_many:
                related_object_manager = getattr(instance, field.get_accessor_name())
                related_objects = list(related_object_manager.all())

                if related_objects:
                    related_objects_to_copy += related_objects

            elif field.many_to_many and hasattr(field, "field"):
                related_object_manager = getattr(instance, field.name)

                relations = list(related_object_manager.all())
                if relations:
                    relations_to_set[field.name] = relations
            else:
                pass
        instance.pk = None

        if callback and callable(callback):
            instance = callback(instance)

        if instance.__class__.__name__ == "Activities":
            instance.ordering = None
        instance.save()

        for related_object in related_objects_to_copy:
            for related_object_field in related_object._meta.fields:
                if related_object_field.related_model == instance.__class__:
                    setattr(related_object, related_object_field.name, instance)
                    new_related_object = self.duplicate_model(
                        related_object, None, True
                    )

                    new_related_object.ordering = None
                    new_related_object.save()

        for field_name, relations in relations_to_set.items():
            field = getattr(instance, field_name)
            field.set(relations)
            text_relations = []
            for relation in relations:
                text_relations.append(str(relation))
        return instance
