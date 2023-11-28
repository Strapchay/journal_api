"""
Test for the User API
"""
from django.test import TestCase
from django.contrib.auth import get_user_model
from django.urls import reverse, resolve
from rest_framework.authtoken.models import Token
from rest_framework.test import APIClient
from rest_framework import status
from django.utils import timezone
from datetime import datetime, timedelta
from core.models import Journal, JournalTables

CREATE_USER_URL = reverse("user:create")
TOKEN_URL = reverse("user:token")
ME_URL = reverse("user:me")
CHANGE_PASSWORD_URL = reverse("user:change_password")
USER_UPDATE_INFO = reverse("user:update_info")
RESET_PWD_URL = reverse("user:password_reset")
JOURNAL_URL = reverse("journal:journal-list")


def create_user(**params):
    """
    Create and return a user
    """
    return get_user_model().objects.create_user(**params)


class PublicUserApiTests(TestCase):
    """
    Test the public features of the user API
    """

    def setUp(self):
        self.client = APIClient()
        self.payload = {
            "first_name": "Test",
            "last_name": "User",
            "username": "testuser",
            "email": "user@example.com",
            "password": "Awesomeuser123",
            "password2": "Awesomeuser123",
        }

    def test_create_user_success(self):
        """
        Test creating a user is successful
        """
        res = self.client.post(CREATE_USER_URL, self.payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        user = get_user_model().objects.get(email=self.payload["email"])

        self.assertTrue(user.check_password(self.payload["password"]))
        self.assertNotIn("password", res.data)

    def test_create_user_success_creates_journal(self):
        """
        Test creating a user creates a default journal
        """
        res = self.client.post(CREATE_USER_URL, self.payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        user = get_user_model().objects.get(email=self.payload["email"])

        self.assertTrue(user.check_password(self.payload["password"]))
        self.assertNotIn("password", res.data)

        user_journal = Journal.objects.filter(user=user)

        self.assertTrue(user_journal.exists())

    def test_create_user_without_matching_password_failure(self):
        """
        Test creating a user fails if the password doesn't match
        """
        self.payload["password2"] = "dajdjfjvadsdf"

        res = self.client.post(CREATE_USER_URL, self.payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_user_with_name_spacing_failure(self):
        """
        Test creating a user fails if the naming is spaced
        """
        self.payload["first_name"] = "dfsdkljsdjsd dsdfsf"
        self.payload["last_name"] = "ksldfjsd dfsdf"
        self.payload["username"] = "ksdlasd sdfasdf"

        res = self.client.post(CREATE_USER_URL, self.payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_user_creates_default_journal_with_journal_tables_and_sets_current_table(
        self,
    ):
        """
        Test creating a user fails if the naming is spaced
        """
        res = self.client.post(CREATE_USER_URL, self.payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)
        user = get_user_model().objects.get(username=self.payload["username"])
        journal = Journal.objects.get(user=user)
        journal_table_first = JournalTables.objects.filter(journal=journal).first()

        self.assertEqual(journal.current_table, journal_table_first.id)

    def test_user_with_email_exists_error(self):
        """
        Test error returned if user with email already exists
        """
        res = self.client.post(CREATE_USER_URL, self.payload)
        self.assertEqual(res.status_code, status.HTTP_201_CREATED)

        res2 = self.client.post(CREATE_USER_URL, self.payload)
        self.assertEqual(res2.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_too_short_error(self):
        """
        Test an error is returned ifi password less than 5 chars
        """
        self.payload["password"] = self.payload["password2"] = "dkvadk"

        res = self.client.post(CREATE_USER_URL, self.payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

        user_exists = (
            get_user_model().objects.filter(email=self.payload["email"]).exists()
        )
        self.assertFalse(user_exists)

    def test_create_token_for_user(self):
        """
        Test creating token for a user is successful
        """
        self.payload.pop("password2")
        user = create_user(**self.payload)
        user.is_active = True
        user.save()
        self.client.force_authenticate(user)

        payload = {"email": self.payload["email"], "password": self.payload["password"]}
        res = self.client.post(TOKEN_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertIn("token", res.data)

    def test_create_token_bad_credentials(self):
        """
        Test creating a token with a bad credentials
        fails
        """
        self.payload.pop("password2")
        user = create_user(**self.payload)
        user.is_active = True
        user.save()
        self.client.force_authenticate(user)

        payload = {"email": self.payload["email"], "password": "dkfljasdf"}

        res = self.client.post(TOKEN_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_blank_password(self):
        """
        Test creating a token with a blank password fails
        """
        self.payload.pop("password2")
        user = create_user(**self.payload)
        user.is_active = True
        user.save()
        payload = {"email": self.payload["email"], "password": ""}
        res = self.client.post(TOKEN_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_create_token_with_expiration_elapse_expires_token(self):
        """
        Test that the created token expires after the expiration timeframe
        """
        self.payload.pop("password2")
        user = create_user(**self.payload)
        user.is_active = True
        user.save()
        payload = {"email": self.payload["email"], "password": self.payload["password"]}
        res = self.client.post(TOKEN_URL, payload)

        self.assertIn("token", res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        res_token = res.data["token"]

        token = Token.objects.get(user=user)
        token.created = timezone.now() - timedelta(3)

        res_get_journals = self.client.get(JOURNAL_URL, HTTP_AUTHORIZATION=res_token)

        self.assertEqual(res_get_journals.status_code, status.HTTP_401_UNAUTHORIZED)

        # token = Token.objects.get(user=user)
        # token.created = timezone.now() - timedelta(3)

        # TODO: test creating a resource with the token fails

    def test_create_token_and_expire_token_and_token_updated_when_new_token_requested(
        self,
    ):
        """
        Test that a new token is created after a token has expired
        """
        self.payload.pop("password2")
        user = create_user(**self.payload)
        user.is_active = True
        user.save()
        payload = {"email": self.payload["email"], "password": self.payload["password"]}
        res = self.client.post(TOKEN_URL, payload)
        self.assertIn("token", res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        res_token = res.data["token"]

        token = Token.objects.get(user=user)
        token.created = timezone.now() - timedelta(3)
        token.save()
        res_get_journals = self.client.get(JOURNAL_URL, HTTP_AUTHORIZATION=res_token)
        self.assertEqual(res_get_journals.status_code, status.HTTP_401_UNAUTHORIZED)

        res_new_token = self.client.post(TOKEN_URL, payload)
        self.assertIn("token", res.data)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertNotEqual(res_new_token.data["token"], res_token)

    def test_retrieve_user_unauthorize(self):
        """
        Test authentication is required for users to be able to retrieve their resources
        """
        self.payload.pop("password2")
        user = create_user(**self.payload)
        res = self.client.get(ME_URL)

        self.assertEqual(res.status_code, status.HTTP_401_UNAUTHORIZED)

    def test_reset_password(self):
        """
        Test resetting a user's password
        """
        user_payload = self.payload.copy()
        user_payload.pop("password2")
        user_payload["email"] = "ayanelaw@outlook.com"
        user = create_user(**user_payload)
        payload = {"email": user_payload["email"]}
        res = self.client.post(RESET_PWD_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)


class PrivateUserApiTests(TestCase):
    """
    Test User API requests that require authentication
    """

    def setUp(self):
        self.payload = {
            "email": "user@example.com",
            "username": "testuser",
            "first_name": "Test",
            "last_name": "User",
            "password": "Awesomeuser123",
        }

        self.user = create_user(**self.payload)
        self.user.is_active = True
        self.user.save()
        self.client = APIClient()
        self.client.force_authenticate(user=self.user)

    def test_retrieve_profile_success(self):
        """
        Test retrieving profile for logged in user
        """
        res = self.client.get(ME_URL)
        self.assertEqual(res.status_code, status.HTTP_200_OK)
        user = self.payload
        user.pop("password")
        self.assertEqual(res.data, user)

    def test_post_me_not_allowed(self):
        """
        Test POST request not allowed for the me endpoint
        """
        payload = {"first_name": "dfjdlsdfsf", "last_name": "kdfldf"}

        res = self.client.post(ME_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_405_METHOD_NOT_ALLOWED)

    def test_update_user_profile(self):
        """
        Test updating a user profile is successful
        """
        payload = {
            "first_name": "kdfosdf",
            "last_name": "kdlfjldfa",
            "email": "sdfasdf@example.com",
            "username": "ts",
        }

        res = self.client.put(USER_UPDATE_INFO, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)
        self.assertEqual(res.data["email"], payload["email"])

    def test_password_change_for_authenticated_user_with_bad_credentials(self):
        """
        Test changing password for authenticated user with bad credentials
        """
        payload = {
            "old_password": self.payload["password"],
            "password": "skdjovadff",
            "password2": "dkvjidfsf",
        }

        res = self.client.put(CHANGE_PASSWORD_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_password_change_for_authenticated_user_with_right_credential(self):
        """
        Test password change for authenticated user with the right credentials is successful
        """
        payload = {
            "old_password": self.payload["password"],
            "password": "Awesomeuser",
            "password2": "Awesomeuser",
        }

        res = self.client.put(CHANGE_PASSWORD_URL, payload)

        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertTrue(self.user.check_password(payload["password"]))

    def test_change_password_to_current_password_fails(self):
        """
        Test a password change to the current password fails
        """
        payload = {
            "old_password": self.payload["password"],
            "password": self.payload["password"],
            "password2": self.payload["password"],
        }

        res = self.client.put(CHANGE_PASSWORD_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_update_user_info_with_right_credential(self):
        """
        Test that the user info can be updated successfully with thee right credentials
        """
        self.payload.pop("password")
        self.payload["email"] = "dkfja@example.com"

        res = self.client.put(USER_UPDATE_INFO, self.payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

    def test_change_password_without_matching_password_fails(self):
        """
        Test that changing a user's password without matching password fails
        """
        payload = {
            "old_password": self.payload["password"],
            "password": "dlfjdsfjlasdjf",
            "password2": "dskflvsd",
        }

        res = self.client.put(CHANGE_PASSWORD_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_400_BAD_REQUEST)

    def test_change_password_with_matching_password_succeeds(self):
        """
        Test change password with matching password succeeds
        """
        payload = {
            "old_password": self.payload["password"],
            "password": "Awesomeuser",
            "password2": "Awesomeuser",
        }
        res = self.client.put(CHANGE_PASSWORD_URL, payload)
        self.assertEqual(res.status_code, status.HTTP_200_OK)

        self.assertTrue(self.user.check_password(payload["password"]))
