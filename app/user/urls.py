from django.urls import re_path, include
from user import views
from django.contrib.auth import views as auth_views

app_name = "user"

urlpatterns = [
    re_path("create/", views.CreateUserView.as_view(), name="create"),
    re_path("token/", views.CreateTokenView.as_view(), name="token"),
    re_path("me/", views.ManageUserView.as_view(), name="me"),
    re_path(
        "change_password/", views.ChangePasswordView.as_view(), name="change_password"
    ),
    re_path(
        "update_info/",
        views.UpdateInfoView.as_view(),
        name="update_info",
    ),
    re_path(
        "password-reset/", views.ResetUserPasswordView.as_view(), name="password_reset"
    ),
    re_path(
        "password-reset-confirm/",
        views.ConfirmResetUserPasswordView.as_view(uid="uidb64", token="token"),
        name="password_reset_confirm",
    ),
]
