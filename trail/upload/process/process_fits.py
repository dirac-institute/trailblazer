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


#def store_header(fitsPath):
#    hdulist = fits.open(fitsPath)
#    hdu = hdulist['PRIMARY']
#    header = hdu.header
#
#    # SDSS has a weird JD time stored, divide for MJD
#    tai = float(header["tai"]) / (24.0*3600.0)
#    t = Time(tai, scale='tai', format='mjd')
#
#    queryData = {
#        "run": int(header["run"]),
#        "camcol": int(header["camcol"]),
#        "filter": str(header["filter"]),
#        "field": int(header["frame"]),
#        "ctype": float(header["crpix1"]),
#        "crpix1": float(header["crpix1"]),
#        "crpix2": float(header["crpix2"]),
#        "crval1": float(header["crval1"]),
#        "crval2": float(header["crval2"]),
#        "cd11": float(header["cd1_1"]),
#        "cd12": float(header["cd1_2"]),
#        "cd21": float(header["cd2_1"]),
#        "cd22": float(header["cd2_2"]),
#        "t": t.isot
#    }
#
#    # this does not seem to raise a primary key violation
#    frame = ExampleFrame(**queryData)
#    frame.save()

def store_header(fitsPath):

    queryData = {}

    # see about edgecases later, as is it seems this always
    # reads the primary header
    md = read_basic_metadata_from_file(filePath, 1)

    translatorClass = amt.MetadataTranslator.determine_translator(md, fitsPath)

    hdu = fits.open(fitsPath)
    header = hdu[0].header
    image = hdu[1].data

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
    centerRa, centerDec = centerSkyCoord.ra.to(u.deg), centerSkyCoord.dec.to(u.deg)

    cornerSkyCoord = wcs.pixel_to_world(0, 0)
    cornerRa, cornerDec = cornerSkyCoord.ra.to(u.deg), cornerSkyCoord.dec.to(u.deg)

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

    try:
        # figure out if and when this isn't degree
        # what else is used translate_unit_to_astrpy...
        cunit = wcs.wcs.cunit
    except AttributeError:
        cunit = u.deg
    queryData["crval1"] = wcs.wcs.crval[0]
    queryData["crval2"] = wcs.wcs.crval[1]
    if cunit != u.deg:
        crval1 = wcs.wcs.crval[0] * cunit
        crval2 = wcs.wcs.crval[1] * cunit
        queryData["crval1"] = crval1.to(u.deg)
        queryData["crval2"] = crval2.to(u.deg)

    

    translatedHDU = translatorClass(header, filename=fitsPath)

    queryData["datetimeBegin"] = translatedHDU.to_datetime_begin()
    queryData["datetimeEnd"] = translatedHDU.to_datetime_end()

#    frame = ExampleFrame(**queryData)
#    frame.save()


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
