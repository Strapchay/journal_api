"""
Views For the Journal
"""
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiExample,
    OpenApiResponse,
)
from rest_framework import viewsets, mixins
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
from core.models import Journal, JournalTables, Tags, Activities
from journal import serializers


class JournalViewSet(
    # mixins.CreateModelMixin,
    # mixins.UpdateModelMixin,
    # mixins.RetrieveModelMixin,
    # viewsets.GenericViewSet,
    viewsets.ModelViewSet
):
    """
    Viewset for creating journal
    """

    authentication_classes = [TokenAuthentication]
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


class JournalTableViewSet(
    # mixins.CreateModelMixin, mixins.UpdateModelMixin,
    viewsets.ModelViewSet
):
    """
    Viewset for creating journal table
    """

    authentication_classes = [TokenAuthentication]
    serializer_class = serializers.JournalTableSerializer
    permission_classes = [IsAuthenticated]
    queryset = JournalTables.objects.all()

    def perform_create(self, serializer):
        """
        Create a new journal table
        """
        journal = get_object_or_404(Journal, id=self.request.data.get("journal"))
        # if self.request.user.is_authenticated:
        if journal is not None:
            serializer.save(journal=journal)

    def get_queryset(self):
        """
        Filter queryset to authenticated user
        """
        queryset = self.queryset
        return queryset.filter(journal__user=self.request.user)


class TagsViewSet(viewsets.ModelViewSet):
    """
    Viewset for creating journal table
    """

    authentication_classes = [TokenAuthentication]
    serializer_class = serializers.TagsSerializer
    permission_classes = [IsAuthenticated]
    queryset = Tags.objects.all()

    def perform_create(self, serializer):
        """
        Create a new journal table
        """
        if self.request.user.is_authenticated:
            serializer.save(user=self.request.user)

    def get_queryset(self):
        """
        Filter queryset to authenticated user
        """
        queryset = self.queryset
        return queryset.filter(
            Q(tag_user=self.request.user) | Q(tag_user__is_superuser=True)
        )


class ActivitiesViewSet(viewsets.ModelViewSet):
    """
    Viewset for creating a journal table activities
    """

    authentication_classes = [TokenAuthentication]
    serializer_class = serializers.ActivitiesSerializer
    permission_classes = [IsAuthenticated]
    queryset = Activities.objects.all()

    def perform_create(self, serializer):
        serializer.save()

    def get_queryset(self):
        return self.queryset.filter(journal_table__journal__user=self.request.user)
