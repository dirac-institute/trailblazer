import os.path

from django.conf import settings
from ..models import ExampleFrame

import matplotlib.pyplot as plt
import astropy.visualization as aviz
from astropy.time import Time
import astropy.units as u
from astropy.io import fits
from astropy.wcs import WCS

import numpy as np

import astro_metadata_translator as amt
from astro_metadata_translator.file_helpers import read_basic_metadata_from_file

"""Dino's initial SDSS-based FITS processing utility."""


__all__ = ["process_fits"]


def store_fits(img):
    tgtPath = os.path.join(settings.FITS_STORAGE_ROOT, f"{img.name}")
    with open(tgtPath, "wb") as f:
        f.write(img.read())
    return tgtPath


def store_header(fitsPath):
    queryData = {}

    hdu = fits.open(fitsPath)
    header = hdu[0].header
    image = hdu[1].data
    fname = os.path.basename(fitsPath)

    dimX, dimY = image.shape
    centerX = int(dimX/2)
    centerY = int(dimY/2)

    # note test if a header doesn't actually have a valid WCS
    # what is the error raised
    wcs = WCS(header)

    queryData["ctype" ] = wcs.wcs.ctype
    queryData["crpix1"] = wcs.wcs.crpix[0]
    queryData["crpix2"] = wcs.wcs.crpix[1]

    centerSkyCoord = wcs.pixel_to_world(centerX, centerY)
    centerRa = centerSkyCoord.ra.to(u.deg)
    centerDec = centerSkyCoord.dec.to(u.deg)

    cornerSkyCoord = wcs.pixel_to_world(0, 0)
    cornerRa = cornerSkyCoord.ra.to(u.deg)
    cornerDec = cornerSkyCoord.dec.to(u.deg)

    unitSphereCenter = np.array([
        np.cos(centerDec) * np.cos(centerRa),
        np.cos(centerDec) * np.sin(centerRa),
        np.sin(centerDec)
    ])

    unitSphereCorner = np.array([
        np.cos(cornerDec) * np.cos(cornerRa),
        np.cos(cornerDec) * np.sin(cornerRa),
        np.sin(cornerDec)
    ])

    unitRadius = np.linalg.norm(unitSphereCenter-unitSphereCorner)
    queryData["radius"] = unitSphereCorner[2]

    queryData["centerX"] = unitSphereCenter[0]
    queryData["centerY"] = unitSphereCenter[1]
    queryData["centerZ"] = unitSphereCenter[2]

    queryData["cornerX"] = unitSphereCorner[0]
    queryData["cornerY"] = unitSphereCorner[1]
    queryData["cornerZ"] = unitSphereCorner[2]

    # see about edgecases later, as is it seems this always
    # reads the primary header
    translator = amt.MetadataTranslator.determine_translator(hdu[0].header, filename=fname)

    if translator.can_translate(header, filename=fname):
        translated = translatorClass(header, filename=fitsPath)

        location = translated.to_location()


        queryData["obs_lon"] = location.lon.value
        queryData["obs_lat"] = location.lat.value
        queryData["obs_height"] = location.height.value

        # translator names are easy everyday names
        # the rest I don't know how they'll vary over different
        # instruments but I can assume potentially by a lot?
        queryData["name"] = translated.name
        queryData["instrument"] = translated.to_instrument()
        queryData["telescope"] = translated.to_telescope()
        queryData["science_program"] = translated.to_science_program()

        queryData["datetimeBegin"] = translated.to_datetime_begin()
        queryData["datetimeEnd"] = translated.to_datetime_end()

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
