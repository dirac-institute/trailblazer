from django.shortcuts import render
from django.apps import apps
from urllib.parse import urlparse
import numpy as np
from trail.settings import GALLERY_IMAGE_COUNT

Metadata = apps.get_model('upload', 'Metadata')
Thumbnails = apps.get_model('upload', 'Thumbnails')
Wcs = apps.get_model('upload', 'Wcs')

"""This code runs when a user visits the 'gallery' URL."""


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
        A list of image objects that have image location and wcs_id
    """
    images = []
    # getting the data from database
    image_data = Thumbnails.objects.all()[page * count:(page + 1) * count]
    images = image_data.values("small", "wcs_id")
    return images


def render_gallery(request):
    """Processes the user request and renders the gallery page
    or if it is a post request returns information on the next set of images.
    The input value count is for how many images per request.
    """
    number_of_pages = int(
        np.ceil(Thumbnails.objects.count() / GALLERY_IMAGE_COUNT))  # might want to cache this once it gets too large
    if request.method == 'GET':
        images = get_images(GALLERY_IMAGE_COUNT, 0)
        return render(request, "gallery.html", {'data': images, "page": 0, "num_of_page": number_of_pages})
    elif request.method == 'POST':
        # checks to see if the request is an integer or not, this removes errors from if user inputs a string value
        try:
            page = int(request.body)
        except TypeError and ValueError:
            page = 0
        # this checks to see that the page referenced is a valid page
        if page >= number_of_pages:
            page = number_of_pages - 1
        elif page < 0:
            page = 0
        images = get_images(GALLERY_IMAGE_COUNT, page)
        return render(request, "gallery_table.html",
                      {'data': images, "page": page, "num_of_page": number_of_pages})


def render_image(request):
    """Processes the users request and renders the image page
    """
    parsed = urlparse(request.get_full_path())
    wcs_id = parsed.query
    image_data = Wcs.objects.prefetch_related("metadata", "thumbnails").get(id=wcs_id)
    return render(request, "images.html", {'image_data': image_data.metadata, "image": image_data.thumbnails})
