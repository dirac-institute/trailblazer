from django.shortcuts import render
from django.conf import settings
from django.apps import apps
from django.http import JsonResponse
import numpy as np
import os

Metadata = apps.get_model('upload', 'Metadata')
Thumbnails = apps.get_model('upload', 'Thumbnails')
Wcs = apps.get_model('upload', 'Wcs')

"""This code runs when a user visits the 'gallery' URL."""


def date_sort(e):
    return e["date"]


def get_images(count, page):
    images = []
    # Would there maybe a way to sort the data without converting to a list?
    # converting to a list seems computationally heavy
    # getting the data from database
    image_data = list(Thumbnails.objects.values())[page * count:(page + 1) * count]

    # sorting data by date

    # processing data for sending to user
    # this code seems inefficient, there is probably a less computational heavy approach.
    for image in image_data:
        wcs_data = Wcs.objects.values()[image["wcs_id"] - 1]
        metadata = Metadata.objects.values()[wcs_data["metadata_id"] - 1]
        images.append({"name": image["small"],
                       "id": image["wcs_id"],
                       "caption": metadata["telescope"],
                       "date": metadata["datetime_begin"]})
    # sorting the images by date with newest images first.
    images.sort(reverse=True, key=date_sort)
    return images


def render_gallery(request, count=12):
    # this function renders the gallery page and also sends the next page information.
    number_of_pages = int(np.ceil(len(Thumbnails.objects.values()) / count))
    if request.method == 'GET':
        images = get_images(count, 0)
        return render(request, "gallery.html", {'data': images, "page": 0, "num_of_page": range(number_of_pages)})
    elif request.method == 'POST':
        try:
            page = int(request.body)
        except:
            page = 0
        images = get_images(count, page)
        return JsonResponse({'data': images})


def render_image(request):
    # this is the code that sends to the image page
    id = int(request.get_full_path_info().split("?")[1])
    image_data = Thumbnails.objects.filter(wcs_id=id)[0]
    wcs_data = Wcs.objects.values()[id - 1]
    metadata = Metadata.objects.values()[wcs_data["metadata_id"] - 1]
    return render(request, "images.html", {'image_data': metadata, 'image': image_data})
