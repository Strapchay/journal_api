"""
Views for the user
"""
from rest_framework import generics, permissions, status
from rest_framework.settings import api_settings
from rest_framework.authtoken.views import ObtainAuthToken
from rest_framework.authtoken.models import Token
from drf_spectacular.utils import (
    extend_schema,
    extend_schema_view,
    OpenApiParameter,
    OpenApiExample,
)
from drf_spectacular.types import OpenApiTypes
from user.serializers import (
    UserSerializer,
    UserCreateSerializer,
    AuthTokenSerializer,
    ChangePasswordSerializer,
    UpdateUserSerializer,
)
from .authentication import ExpiringTokenAuthentication
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.utils.translation import gettext as _
from rest_framework.response import Response
from datetime import timedelta
from dj_rest_auth.views import PasswordResetConfirmView, PasswordResetView


class CreateUserView(generics.CreateAPIView):
    """
    Views for creating a new user in the system
    """

    serializer_class = UserCreateSerializer


@extend_schema_view(
    post=extend_schema(
        description="Create/Generate Auth token for user's requests",
        examples=[
            OpenApiExample(
                "Request Body", value={"email": "string", "password": "string"}
            ),
        ],
    )
)
class CreateTokenView(ObtainAuthToken):
    """
    View to Generate Auth token for users requests
    """

    serialiizer_class = AuthTokenSerializer
    renderer_classes = api_settings.DEFAULT_RENDERER_CLASSES

    def post(self, request):
        serializer = self.serialiizer_class(data=request.data)
        if serializer.is_valid():
            token, created = Token.objects.get_or_create(
                user=serializer.validated_data["user"]
            )

            current_time = timezone.now()
            if not created and token.created < (current_time - timedelta(3)):
                token.delete()
                token = Token.objects.create(user=serializer.validated_data["user"])
                token.created = current_time
                token.save()

            return Response({"token": token.key})
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@extend_schema_view(
    get=extend_schema(description="Returns user's details if the user is authenticated")
)
class ManageUserView(generics.RetrieveAPIView):
    """
    Manage the authenticated user
    """

    serializer_class = UserSerializer
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        """
        Retrieve and return the authenticated user
        """
        return self.request.user


@extend_schema_view(
    put=extend_schema(description="Change Users Password"),
)
class ChangePasswordView(generics.UpdateAPIView):
    queryset = get_user_model()
    authentication_classes = [ExpiringTokenAuthentication]
    permissions_classes = [permissions.IsAuthenticated]
    serializer_class = ChangePasswordSerializer
    http_method_names = ["put"]

    def get_object(self):
        """
        Retrieve and return the authenticated user
        """
        return self.request.user


@extend_schema_view(
    put=extend_schema(description="Update Users Profile"),
)
class UpdateInfoView(generics.UpdateAPIView):
    queryset = get_user_model()
    authentication_classes = [ExpiringTokenAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UpdateUserSerializer
    http_method_names = ["put"]

    def get_object(self):
        """
        Retrieve and return the authenticated user
        """
        return self.request.user


class ResetUserPasswordView(PasswordResetView):
    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        return context


class ConfirmResetUserPasswordView(PasswordResetConfirmView):
    """
    View for resetting user's password
    """

    uid = None
    token = None

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response({"detail": _("Password reset successfully")})
