from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.exceptions import ValidationError
from rest_framework import status


class BatchSerializerMixin:
    """
    Mixin to be subclassed by all batch related serializer mixins
    """

    def to_internal_value(self, data):
        list_instance_exists_in_context = False
        list_instances = ["batch_duplicate_activities"]
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

    def validate_tag_ids(self, data, unique=True):
        if isinstance(data, list):
            tag_list = [int(i) for i in data]
            if unique and len(tag_list) != len(set(tag_list)):
                raise ValidationError(
                    "Cannot make multiple request operation on a single instance"
                )

            return tag_list
        return [data]


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
        # try:
        ids = self.validate_ids(request.data["duplicate_list"][0]["ids"])
        print("the ids", ids)

        queryset = self.get_object()
        print("the dup queryseeet", queryset)

        serializer = self.get_serializer(
            queryset,
            data=request.data["duplicate_list"],
            partial=True,
            many=True,
            type=self.action,
        )

        serializer.is_valid(raise_exception=True)
        print("serializeer dup passed val")
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    # except Exception as e:
    #     raise ValidationError(e)
