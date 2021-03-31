import os.path

from django.conf import settings
from ..models import ExampleFrame

import matplotlib.pyplot as plt
import astropy.visualization as aviz
from astropy.time import Time
from astropy.io import fits

"""Dino's initial SDSS-based FITS processing utility."""


__all__ = ["process_fits"]


def store_fits(img):
    tgtPath = os.path.join(settings.FITS_STORAGE_ROOT, f"{img.name}")
    with open(tgtPath, "wb") as f:
        f.write(img.read())
    return tgtPath


def store_header(fitsPath):
    hdulist = fits.open(fitsPath)
    hdu = hdulist['PRIMARY']
    header = hdu.header

    # SDSS has a weird JD time stored, divide for MJD
    tai = float(header["tai"]) / (24.0*3600.0)
    t = Time(tai, scale='tai', format='mjd')

    queryData = {
        "run": int(header["run"]),
        "camcol": int(header["camcol"]),
        "filter": str(header["filter"]),
        "field": int(header["frame"]),
        "ctype": float(header["crpix1"]),
        "crpix1": float(header["crpix1"]),
        "crpix2": float(header["crpix2"]),
        "crval1": float(header["crval1"]),
        "crval2": float(header["crval2"]),
        "cd11": float(header["cd1_1"]),
        "cd12": float(header["cd1_2"]),
        "cd21": float(header["cd2_1"]),
        "cd22": float(header["cd2_2"]),
        "t": t.isot
    }

    # this does not seem to raise a primary key violation
    frame = ExampleFrame(**queryData)
    frame.save()


def store_thumbnail(fitsPath):
    hdulist = fits.open(fitsPath)
    hdu = hdulist['PRIMARY']
    image = hdu.data

    norm = aviz.ImageNormalize(image, stretch=aviz.HistEqStretch(image))
    normedImage = norm(image)

    # contains fits extension, we want PNG for thumbs
    name = os.path.split(fitsPath)[-1]
    basename = name.split('.')[0]
    savePath = os.path.join(settings.MEDIA_ROOT, basename+'.png')

    plt.imsave(savePath, normedImage)


def process_fits(img):
    fitsFilePath = store_fits(img)
    store_header(fitsFilePath)
    store_thumbnail(fitsFilePath)
