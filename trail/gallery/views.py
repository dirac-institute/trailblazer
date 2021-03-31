from django.shortcuts import render
from django.conf import settings
import os

"""This code runs when a user visits the 'gallery' URL."""


def get_images(count):
    images = []
    path = os.path.join(settings.MEDIA_ROOT)
    try:
        imageNames = os.listdir(path)
    except FileNotFoundError:
        return []
    else:
        for i, imageName in enumerate(imageNames):
            images.append({"name": imageName,
                           "path": os.path.join(path, imageName),
                           "caption": i})
        return images


def render_gallery(request, count=20):
    images = get_images(count)
    return render(request, "gallery.html", {'data': images})
