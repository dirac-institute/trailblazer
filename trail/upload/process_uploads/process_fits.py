from abc import abstractmethod
import os.path
from pathlib import Path

from django.conf import settings
from ..models import Frame

from PIL import Image
import numpy as np
import matplotlib.pyplot as plt

import astropy.visualization as aviz
from astropy.time import Time
import astropy.units as u
from astropy.io import fits
from astropy.wcs import WCS

import astro_metadata_translator as translate
from astro_metadata_translator.file_helpers import read_basic_metadata_from_file

"""Dino's initial SDSS-based FITS processing utility."""


__all__ = ["process_fits"]


class TemporaryUploadedFileWrapper:
    def __init__(self, upload):
        self.tmpfile = upload
        self.filename = upload.name

    @property
    def extension(self):
        special = {".gz", ".bz2", ".xz", ".fz"}

        fname = Path(self.filename)
        extensions = fname.suffixes
        if not extensions:
            return ""

        ext = extensions.pop()

        if extensions and ext in special:
            return "".join(extensions)

        return ext

    @property
    def basename(self):
        return self.filename.split(self.extension)[0]


    def save(self):
        #TODO: fix os.path when transitioning to S3
        # make the destination configurable
        tgtPath = os.path.join(settings.STATIC_ROOT, f"upload/fits/{self.filename}")

        with open(tgtPath, "wb") as f:
            f.write(self.tmpfile.read())

        return tgtPath


class UploadProcessor:
    processors = dict()

    def __init__(self, uploadWrapper):
        self._upload = uploadWrapper

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        UploadProcessor.processors[cls.name] = cls

    @classmethod
    @abstractmethod
    def can_process(self, upload):
        raise NotImplemented()

    @classmethod
    def process(cls, upload):
        for processor in cls.processors.values():
            if processor.can_process(upload):
                uploadHandler = processor(upload)
                uploadHandler.store_header()
                #uploadHandler.detect_trails()
                uploadHandler.store_thumbnails()


class FitsProcessor(UploadProcessor):
    name = "FitsProcessor"
    extensions = [".fits", ]

    def __init__(self, upload):
        super().__init__(upload)

        self.hdu = fits.open(self._upload.tmpfile.temporary_file_path())
        self.header = self.hdu["PRIMARY"].header
        self.image = self.hdu["PRIMARY"].data

    @classmethod
    def can_process(cls, fitsImage):
        if fitsImage.extension in cls.extensions:
            return True
        return False

    def standardized_wcs(self):
        # note test if a header doesn't actually have a valid WCS
        # what is the error raised
        standardizedWcs = {}
        wcs = WCS(self.header)

        dimX, dimY = self.image.shape
        centerX = int(dimX/2)
        centerY = int(dimY/2)

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

        # do we really need this?
        #standardizedWcs["ctype"] = wcs.wcs.ctype
        #standardizedWcs["crpix1"] = wcs.wcs.crpix[0]
        #standardizedWcs["crpix2"] = wcs.wcs.crpix[1]

        standardizedWcs["radius"] = unitRadius

        standardizedWcs["center_x"] = unitSphereCenter[0]
        standardizedWcs["center_y"] = unitSphereCenter[1]
        standardizedWcs["center_z"] = unitSphereCenter[2]

        standardizedWcs["corner_x"] = unitSphereCorner[0]
        standardizedWcs["corner_y"] = unitSphereCorner[1]
        standardizedWcs["corner_z"] = unitSphereCorner[2]

        return standardizedWcs

    def standardized_header_metadata(self):
        standardizedKeys = {}

        # see about edgecases later, as is it seems this always
        # reads the primary header
        translator = translate.MetadataTranslator.determine_translator(self.header,
                                                                       filename=self._upload.filename)

        if translator.can_translate(self.header, filename=self._upload.filename):
            translated = translator(self.header, filename=self._upload.filename)

            location = translated.to_location()

            standardizedKeys["obs_lon"] = location.lon.value
            standardizedKeys["obs_lat"] = location.lat.value
            standardizedKeys["obs_height"] = location.height.value

            # translator names are easy everyday names
            # the rest I don't know how they'll vary over different
            # instruments but I can assume potentially by a lot?
            standardizedKeys["name"] = translated.name
            standardizedKeys["telescope"] = translated.to_telescope()
            standardizedKeys["instrument"] = translated.to_instrument()
            standardizedKeys["science_program"] = translated.to_science_program()

            standardizedKeys["datetime_begin"] = translated.to_datetime_begin().isot
            standardizedKeys["datetime_end"] = translated.to_datetime_end().isot

        return standardizedKeys

    def store_header(self):
        insertData = self.standardized_wcs()
        insertData.update(self.standardized_header_metadata())

        frame = Frame(**insertData)
        frame.save()

    def normalized_image(self):
        # TODO: make things like these configurable (also see resize in
        # store_thumbnail)
        stretch = aviz.HistEqStretch(self.image)
        norm = aviz.ImageNormalize(self.image, stretch=stretch, clip=True)

        return norm(self.image)

    def store_thumbnails(self):
        normedImage = self.normalized_image()

        # TODO: a note to fix os.path dependency when transitioning to S3
        # and fix saving method from plt to boto3
        basename = self._upload.basename
        smallPath = os.path.join(settings.MEDIA_ROOT, basename+'_small.png')
        largePath = os.path.join(settings.MEDIA_ROOT, basename+'_large.png')

        # TODO: consider removing PIL dependency once trail detection is
        # implemented, if it is implemented via OpenCV
        img = Image.fromarray(np.uint8(normedImage*255))

        basewidth = 640
        wpercent = (basewidth / float(img.size[0]))

        hsize = int((float(img.size[1]) * float(wpercent)))
        img = img.resize((basewidth, hsize), Image.ANTIALIAS)

        img.save(smallPath)
        plt.imsave(largePath, normedImage)


def process_fits(img):
    upload = TemporaryUploadedFileWrapper(img)
    uplPrc = UploadProcessor(upload)
    uplPrc.process(upload)
    upload.save()
