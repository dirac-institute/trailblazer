from django.shortcuts import render
from django.conf import settings
from django.apps import apps
import os

Metadata = apps.get_model('upload', 'Metadata')
Thumbnails = apps.get_model('upload', 'Thumbnails')
Wcs = apps.get_model('upload', 'Wcs')


"""This code runs when a user visits the 'gallery' URL."""


def date_sort(e):
    return e["date"]


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
        # getting the data from database
        image_data = list(Thumbnails.objects.values())

        # sorting data by date

        # processing data for sending to user
        for image in image_data:
            wcs_data = Wcs.objects.values()[image["wcs_id"]-1]
            metadata = Metadata.objects.values()[wcs_data["metadata_id"]-1]
            images.append({"name": image["small"],  # at the moment this is just pulling the static files
                           "id": image["wcs_id"],
                           "path": os.path.join(path, image["small"]),
                           "caption": metadata["telescope"],
                           "date": metadata["datetime_begin"]})

        images.sort(reverse=True,key=date_sort)
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
    id = int(request.get_full_path_info().split("?")[1])
    image_data = Thumbnails.objects.filter(wcs_id=id)[0]
    wcs_data = Wcs.objects.values()[id-1]
    metadata = Metadata.objects.values()[wcs_data["metadata_id"]-1]

    print()
    return render(request, "images.html", {'image_data': metadata, 'image': image_data})
