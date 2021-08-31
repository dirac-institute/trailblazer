from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from gallery import views

"""Route gallery URLs to gallery views here."""


urlpatterns = [
    path('', views.render_gallery, name='gallery'),
    path('image', views.render_image, name='image'),
    path('get_images', views.render_gallery, name='get_images'),
] + static(settings.STATIC_URL, document_root=settings.STATIC_ROOT)
