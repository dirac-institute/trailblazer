from django.shortcuts import render
from django.conf import settings
from django.apps import apps
import os

Metadata = apps.get_model('upload', 'Metadata')
Thumbnails = apps.get_model('upload', 'Thumbnails')

"""This code runs when a user visits the 'gallery' URL."""


def date_sort(e):
    return e["datetime_begin"]


def get_images(count):
    images = []
    path = os.path.join(settings.MEDIA_ROOT)
    try:
        imageNames = os.listdir(path)
    except FileNotFoundError:
        return []
    else:
        # Would there maybe a way to sort the data without converting to a list?
        # converting to a list seems computationally heavy
        print(Thumbnails.objects.values())
        # getting the data from database
        data = list(Metadata.objects.values())

        # sorting data by date
        data.sort(reverse=True, key=date_sort)
        print(data)

        # processing data for sending to user
        for image in data:
            images.append({"name": imageNames[0],  # at the moment this is just pulling the static files
                           "id": image["id"],
                           "path": os.path.join(path, imageNames[0]),
                           "caption": image["telescope"],
                           "date": image["datetime_begin"]})
        # for i, imageName in enumerate(imageNames):
        #     images.append({"name": imageName,
        #                    "path": os.path.join(path, imageName),
        #                    "caption": imageName,
        #                    "date": "undefined"})
        return images


def render_gallery(request, count=20):
    images = get_images(count)
    return render(request, "gallery.html", {'data': images})

def render_image(request):
    image_data = Metadata.objects.filter(id=int(request.get_full_path_info().split("?")[1]))[0]
    return render(request, "images.html", {'image_data': image_data})
