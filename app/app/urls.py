"""
URL configuration for app project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/4.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import re_path,include
from django.conf.urls.static import static
from django.conf import settings
from drf_spectacular.views import SpectacularAPIView,SpectacularSwaggerView

from core import views as core_views


urlpatterns = [
    re_path('admin/', admin.site.urls),
    re_path("api/schema/", SpectacularAPIView.as_view(),name="api-schema"),
    re_path("api/docs/",SpectacularSwaggerView.as_view(url_name="api-schema"),name="api-docs"),
    re_path("api/user/",include("user.urls")),
    re_path("api/journal/", include("journal.urls")),
    re_path("api/healthcheck", core_views.health_check,name="healthcheck"),
]
if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL,document_root=settings.MEDIA_ROOT)
