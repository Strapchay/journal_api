from django.urls import re_path, include
from journal import views
from rest_framework.routers import DefaultRouter

router = DefaultRouter()
router.register("journals", views.JournalViewSet)
router.register("journal-tables", views.JournalTableViewSet)
router.register("tags", views.TagsViewSet)
router.register("activities", views.ActivitiesViewSet)
router.register("intentions", views.IntentionsViewSet)
router.register("happenings", views.HappeningsViewSet)
router.register("grateful-for", views.GratefulForViewSet)
router.register("action-items", views.ActionsItemViewSet)


app_name = "journal"

urlpatterns = [
    re_path("", include(router.urls)),
]
