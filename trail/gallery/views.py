from django.shortcuts import render
# from django.conf import settings
from django.apps import apps
from django.http import JsonResponse
import numpy as np

# import os

Metadata = apps.get_model('upload', 'Metadata')
Thumbnails = apps.get_model('upload', 'Thumbnails')
Wcs = apps.get_model('upload', 'Wcs')

"""This code runs when a user visits the 'gallery' URL."""


def date_sort(e):
    """Sort function that sorts by value date
    """
    return e["date"]


def get_images(count, page):
    """
    Obtains images for the gallery from the database

    Parameters
    ----------
    count : integer
        The number images per page.
    page : integer
        The current page number

    Returns
    -------
    images : `list`
        A list of image objects that have image location, id, caption and date
    """

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
        images.append({"name": image["small"].split("\\media\\")[1],
                       "id": image["wcs_id"],
                       "caption": metadata["telescope"],
                       "date": metadata["datetime_begin"]})
    # sorting the images by date with newest images first.
    images.sort(reverse=True, key=date_sort)
    return images


def render_gallery(request, count=12):
    """Processes the user request and renders the gallery page
    or if it is a post request returns information on the next set of images.
    The input value count is for how many images per request.
    """
    number_of_pages = int(np.ceil(len(Thumbnails.objects.values()) / count))
    if request.method == 'GET':
        images = get_images(count, 0)
        return render(request, "gallery.html", {'data': images, "page": 0, "num_of_page": range(number_of_pages)})
    elif request.method == 'POST':
        try:
            page = int(request.body)
        except TypeError:
            page = 0
        images = get_images(count, page)
        return JsonResponse({'data': images})


def render_image(request):
    """Processes the users request and renders the image page
    """
    wcs_id = int(request.get_full_path_info().split("?")[1])
    image_data = Thumbnails.objects.filter(wcs_id=wcs_id)[0]
    wcs_data = Wcs.objects.values()[wcs_id - 1]
    metadata = Metadata.objects.values()[wcs_data["metadata_id"] - 1]
    return render(request, "images.html", {'image_data': metadata, 'image': image_data})
