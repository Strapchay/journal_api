"""
Serializers for the User API view
"""
from django.contrib.auth import get_user_model, authenticate
from django.utils.translation import gettext as _
from django.contrib.auth.hashers import make_password
from django.contrib.auth.password_validation import validate_password
from django.utils.encoding import force_str
from django.utils.http import urlsafe_base64_decode as uid_decoder
from django.contrib.auth.tokens import default_token_generator
from rest_framework import serializers, exceptions
from dj_rest_auth.serializers import (
    PasswordResetSerializer,
    PasswordResetConfirmSerializer,
)
from core.models import Journal
from journal.config import JOURNAL_DESCRIPTION, DEFAULT_JOURNAL_NAME
from journal.serializers import JournalSerializer


class UserSerializer(serializers.ModelSerializer):
    """
    Serializer for the User Object
    """

    class Meta:
        model = get_user_model()
        fields = ["email", "username", "password", "first_name", "last_name"]
        extra_kwargs = {"password": {"write_only": True, "min_length": 5}}

    def create(self, validated_data):
        """
        Create and return a user with encrypted password
        """
        return get_user_model().objects.create_user(**validated_data)


class UserCreateSerializer(serializers.ModelSerializer):
    """
    Serializer to create a new user
    """

    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = get_user_model()
        fields = [
            "email",
            "password",
            "password2",
            "first_name",
            "last_name",
            "username",
        ]
        extra_kwargs = {"password": {"write_only": True, "min_length": 5}}

    def validate_name_spacing(self, attrs):
        invalid_first_name = len(attrs["first_name"].split(" ")) > 1

        invalid_last_name = len(attrs["last_name"].split(" ")) > 1

        invalid_username = len(attrs["username"].split(" ")) > 1

        invalid_attr = (
            invalid_first_name
            and "first_name"
            or invalid_last_name
            and "last_name"
            or invalid_username
            and "username"
        )

        if invalid_attr not in [None, False]:
            raise serializers.ValidationError(
                {invalid_attr: "The naming should not contain a spacing"}
            )

        return attrs

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError(
                {"password": "Password fields didn't match"}
            )

        self.validate_name_spacing(attrs)
        return attrs

    def _create_journal_with_default_values(self, user):
        """
        Creates a default journal on user's signup
        """
        try:
            self.context["user"] = user

            journal_payload = {
                "journal_name": DEFAULT_JOURNAL_NAME,
                "journal_description": JOURNAL_DESCRIPTION,
                "user": user.id,
            }

            journal_serializer = JournalSerializer(
                data=journal_payload, context=self.context
            )
            journal_serializer.is_valid(raise_exception=True)
            journal_serializer.save()

        except Exception as e:
            print("trig exception user journal table", e)

    def create(self, validated_data):
        """
        Create and return a user with encrypted password
        """
        validated_data.pop("password2")

        created_user = get_user_model().objects.create_user(**validated_data)

        self._create_journal_with_default_values(created_user)

        return created_user


class AuthTokenSerializer(serializers.Serializer):
    """
    Serializer for the user auth token
    """

    email = serializers.EmailField()
    password = serializers.CharField(
        style={"input_type": "password"}, trim_whitespace=False
    )

    def validate(self, attrs):
        """
        Validate and authenticate the user
        """
        email = attrs.get("email")
        password = attrs.get("password")
        user = authenticate(
            self.context.get("request"), username=email, password=password
        )

        if user:
            attrs["user"] = user
            return attrs

        raise serializers.ValidationError(
            _("Unable to authenticate user"), code="authorization"
        )

    class Meta:
        fields = ["email", "password"]
        exclude = ["username"]


class ChangePasswordSerializer(serializers.ModelSerializer):
    password = serializers.CharField(
        write_only=True, required=True, validators=[validate_password]
    )
    password2 = serializers.CharField(write_only=True, required=True)
    old_password = serializers.CharField(write_only=True, required=True)

    class Meta:
        model = get_user_model()
        fields = ["old_password", "password", "password2"]

    def validate(self, attrs):
        if attrs["password"] != attrs["password2"]:
            raise serializers.ValidationError(
                {"password": "Password fields didn't match."}
            )
        return attrs

    def validate_old_password(self, value):
        user = self.context["request"].user
        if not user.check_password(value):
            raise serializers.ValidationError(
                {"old_password": "Old password is not correct"}
            )
        return value

    def update(self, instance, validated_data):
        user = self.context["request"].user

        if user.check_password(validated_data["password"]):
            raise serializers.ValidationError(_("New password cannot be Old Password"))

        if user.pk != instance.pk:
            raise serializers.ValidationError(
                _("Unable to authenticate request"), code="authorization"
            )
        instance.set_password(validated_data["password"])
        instance.save()

        return instance


class UpdateUserSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(required=True)

    class Meta:
        model = get_user_model()
        fields = ["email", "first_name", "last_name", "username"]
        extra_kwargs = {
            "first_name": {"required": True},
            "last_name": {"required": True},
        }

    def validate_email(self, value):
        user = self.context["request"].user
        if self.Meta.model.objects.exclude(pk=user.pk).filter(email=value).exists():
            raise serializers.ValidationError({"email": "This email is already in use"})
        return value

    def update(self, instance, validated_data):
        user = self.context["request"].user

        if user.pk != instance.pk:
            raise serializers.ValidationError(
                _("Unable to authenticated request"), code="authorization"
            )

        instance.first_name = validated_data["first_name"]
        instance.last_name = validated_data["last_name"]
        instance.email = validated_data["email"]
        instance.username = validated_data["username"]
        instance.save()
        return instance


class ResetPasswordSerializer(PasswordResetSerializer):
    """
    Serializer to reset users password
    """

    def get_email_options(self):
        return {
            "html_email_template_name": "registration/password_reset_email.html",
        }


class ResetPasswordConfirmSerializer(PasswordResetConfirmSerializer):
    """
    Serializer to for resetting the password confirm view and updating the user password
    """

    def custom_validation(self, attrs):
        self._errors = {}

        # decode the uidb64 to uid to get User object
        try:
            uid = force_str(uid_decoder(attrs["uid"]))
            self.user = get_user_model()._default_manager.get(pk=uid)
        except (TypeError, ValueError, OverflowError, get_user_model().DoesNotExist):
            raise exceptions.ValidationError({"uid": ["Invalid value"]})

        if attrs["new_password1"] != attrs["new_password2"]:
            raise exceptions.ValidationError({"password": ["Password Does Not Match"]})

        if not default_token_generator.check_token(self.user, attrs["token"]):
            raise exceptions.ValidationError({"token": ["Invalid Token Value"]})

        # super(PasswordResetConfirmSerializer, self).validate(attrs)
        return attrs
