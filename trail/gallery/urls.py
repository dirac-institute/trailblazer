from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from gallery.views import render_gallery, render_image

"""Route gallery URLs to gallery views here."""


urlpatterns = [
    path('', render_gallery, name='gallery'),
    path('image', render_image, name='image'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
