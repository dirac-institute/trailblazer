"""trail URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.1/topics/http/urls/
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
from django.contrib.staticfiles.urls import static
from django.conf import settings
from django.urls import path, re_path, include
from django.views.generic import TemplateView
from drf_yasg.views import get_schema_view
from drf_yasg import openapi
from rest_framework import permissions

schema_view = get_schema_view(
   openapi.Info(
      title=settings.API_DOC_TITLE,
      default_version=settings.API_DOC_DEFAULT_VER,
      description=settings.API_DOC_DESCRIPTION,
      terms_of_service="https://www.google.com/policies/terms/",
      contact=openapi.Contact(email=settings.API_DOC_CONTACT_EMAIL),
      license=openapi.License(
          name=settings.API_DOC_LICENSE_NAME,
          url=settings.API_DOC_LICENSE_URL
        ),
   ),
   public=True,
   permission_classes=[permissions.AllowAny],
)

urlpatterns = [
    path(r'admin/', admin.site.urls),
    path(r'gallery/', include('gallery.urls')),
    path(r'query/', include('query.urls')),
    path(r'api_doc', schema_view.with_ui('swagger', cache_timeout=0)),
    # path(r'query/results', include('query.urls')),
    path(r'upload/', include('upload.urls')),
    re_path(r'^about/', TemplateView.as_view(template_name='about.html')),
    # in the new template the index is the gallery, we don't need so many apps
    re_path(r'^index/', include('gallery.urls')),
    re_path(r'^',  include('gallery.urls')),
    # re_path(r'^index/', TemplateView.as_view(template_name='index.html')),
    # re_path(r'^$', TemplateView.as_view(template_name='index.html')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + \
    static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
