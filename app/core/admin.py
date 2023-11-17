from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
import gettext_lazy as _
from core import models

# Register your models here.
class UserAdmin(BaseUserAdmin):
    """
    Admin pages config
    """

    ordering = ["id"]
    list_display = ["email","first_name","last_name"]
    fieldsets = (
        (None, {"fields": ("email","password")}),
        (_("Permissions"), {"fields": ("is_active","is_staff","is_superuser")}),
        (_("Important dates"),{"fields": ("last_login",)}),
    )
    readonly_fields = ["last_login"]
    add_fieldsets = (
        (
            None,
            {
                "classes": ("wide",),
                "fields": (
                    "email",
                    "password1",
                    "password2",
                    "first_name",
                    "last_name",
                    "is_active",
                    "is_staff",
                    "is_superuser"
                ),
            },
        ),
    )

admin.site.register(models.User,UserAdmin)