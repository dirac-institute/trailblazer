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

urlpatterns = [
    path(r'admin/', admin.site.urls),
    path(r'gallery/', include('gallery.urls')),
    path(r'query/', include('query.urls')),
    #path(r'query/results', include('query.urls')),
    path(r'upload/', include('upload.urls')),
    re_path(r'^about/', TemplateView.as_view(template_name='about.html')),
    # in the new template the index is the gallery, we don't need so many apps
    re_path(r'^index/', include('gallery.urls')),
    re_path(r'^',  include('gallery.urls')),
    # re_path(r'^index/', TemplateView.as_view(template_name='index.html')),
    # re_path(r'^$', TemplateView.as_view(template_name='index.html')),
] + static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT) + \
    static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
