from abc import abstractmethod
import warnings
import os.path

from PIL import Image
import numpy as np
import matplotlib.pyplot as plt

import astropy.visualization as aviz
from astropy.time import Time
import astropy.units as u
from astropy.io import fits
from astropy.wcs import WCS, FITSFixedWarning

import astro_metadata_translator as translate
from astro_metadata_translator.file_helpers import read_basic_metadata_from_file

from ..models import Frame
from django.conf import settings


"""Classes that process various types uploaded file(s)."""


__all__ = ["UploadProcessor", "FitsProcessor", ]


class UploadProcessor:
    """Supports processing of a single uploaded file.

    Parameters
    ----------
    uploadWrapper : `tmpfile.temporaryUploadedFileWrapper`
    """

    processors = dict()
    """All registered upload processing classes."""

    media_root = settings.MEDIA_ROOT
    """Root of the location where thumbnails will be stored."""

    def __init__(self, uploadWrapper):
        self._upload = uploadWrapper

    def __init_subclass__(cls, **kwargs):
        # registers all subclasses (of this class) as availible translators
        super().__init_subclass__(**kwargs)
        UploadProcessor.processors[cls.name] = cls

    @classmethod
    @abstractmethod
    def canProcess(self, upload):
        """Returns ``True`` when the processor knows how to handle given
        upload.

        Parameters
        ----------
        upload : `tmpfile.TemporaryUploadedFileWrapper`
            Uploaded file.

        Returns
        -------
        canProcess : `bool`
            `True` when the processor knows how to handle uploaded file and
            `False` otherwise
        """
        raise NotImplemented()

    @classmethod
    def process(cls, upload):
        """Unified interface for handling upload processing. Finds an
        appropriate processor and:
          * stores normalized header data,
          * detects trails and stores measurements and
          * stores thumbnails for gallery

        Parameters
        ----------
        upload : `tmpfile.TemporaryUploadedFileWrapper`
            Uploaded file.
        """
        # TODO: get some error handling here
        for processor in cls.processors.values():
            if processor.canProcess(upload):
                uploadHandler = processor(upload)
                uploadHandler.storeHeader()
                #uploadHandler.detect_trails()
                uploadHandler.storeThumbnails()
                break


class FitsProcessor(UploadProcessor):
    """Suppports processing of a single FITS file.

    Parameters
    ----------
    upload : `tmpfile.TemporaryUploadedFileWrapper`
            Uploaded file.
    """

    name = "FitsProcessor"
    """Processor's name."""

    extensions = [".fit", ".fits", ".fits.fz"]
    """File extensions this processor can handle."""

    def __init__(self, upload):
        super().__init__(upload)

        self.hdulist = fits.open(self._upload.tmpfile.temporary_file_path())
        self.header = self.hdulist["PRIMARY"].header
        self.image = self.hdulist["PRIMARY"].data

    @classmethod
    def canProcess(cls, fitsImage):
        if fitsImage.extension in cls.extensions:
            return True
        return False

    def standardizedWcs(self):
        """Normalizes FITS WCS information read from the header of uploaded
        file and returns a dictionary with standardized, as understood by
        trailblazer, WCS keys.

        Astropy is used to calculate on-sky coordinates, in degrees, of the
        center of the image and of (0, 0)'th corner of the image. These
        coordinates are then projected to a unit sphere and the Cartesian
        components of the resulting points, as well as the distance between
        the center and corner coordiantes, are calculated.

        Returned dict contains the following keys:
        * radius - distance between central and corner pixel on unit sphere
        * center_[x, y, z] - coordinates of central pixel on unit sphere
        * corner_[x, y, z] - coordinates of corner pixel on unit sphere

        Returns
        -------
        standardizedWCS : `dict`
          A dictionary with standardized WCS keys and values.
        """
        # note test if a header doesn't actually have a valid WCS
        # what is the error raised
        standardizedWcs = {}
        # TODO: When eventually logging is added to processing, redirect these
        # warnings to the logs instead of silencing
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", category=FITSFixedWarning)
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

        standardizedWcs["wcs_radius"] = unitRadius

        standardizedWcs["wcs_center_x"] = unitSphereCenter[0]
        standardizedWcs["wcs_center_y"] = unitSphereCenter[1]
        standardizedWcs["wcs_center_z"] = unitSphereCenter[2]

        standardizedWcs["wcs_corner_x"] = unitSphereCorner[0]
        standardizedWcs["wcs_corner_y"] = unitSphereCorner[1]
        standardizedWcs["wcs_corner_z"] = unitSphereCorner[2]

        return standardizedWcs

    def standardizedHeaderMetadata(self):
        """Normalizes FITS header information of the uploaded file and returns
        a dictionary with standardized, as understood by trailblazer, header
        keys.

        Rubin's ``astro_metadata_translator`` is used to perform the
        translation for the most popular instruments.

        Returned dict contains the following keys:
        * obs_[lon, lat, height] - Observatory coordinates
        * name - name of translator class that performed the translation, oten
                 a simple(r) instrument name
        * telescope
        * instrument
        * science_program
        * datetime_[begin, end] - start and end of exposure

        Returns
        -------
        standardizedKeys : `dict`
          A dictionary with standardized header keys and values.
        """
        standardizedKeys = {}

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
            standardizedKeys["metadata_translator_name"] = translated.name
            standardizedKeys["telescope"] = translated.to_telescope()
            standardizedKeys["instrument"] = translated.to_instrument()
            standardizedKeys["science_program"] = translated.to_science_program()

            standardizedKeys["datetime_begin"] = translated.to_datetime_begin().isot
            standardizedKeys["datetime_end"] = translated.to_datetime_end().isot
            standardizedKeys["exposure_duration"] = translated.to_exposure_time().value

            standardizedKeys["physical_filter"] = translated.to_physical_filter()

        return standardizedKeys

    def storeHeader(self):
        """Normalize and insert normalized WCS and header metadata into the
        database.
        """
        # TODO: perhaps some error checking....
        insertData = self.standardizedWcs()
        insertData.update(self.standardizedHeaderMetadata())

        frame = Frame(**insertData)
        frame.save()

    def normalizedImage(self):
        """Normalizes the image data of the uploaded file using histogram
        equalization.

        Returns
        -------
        norm : `np.array`
            Normalized image.
        """
        # TODO: make things like these configurable (also see resize in
        # store_thumbnail)
        stretch = aviz.HistEqStretch(self.image)
        norm = aviz.ImageNormalize(self.image, stretch=stretch, clip=True)

        return norm(self.image)

    def storeThumbnails(self):
        """Normalizes image data of the uploaded file and creates a small
        (640 pixels high) and a large (1:1) thumbnails.
        """
        normedImage = self.normalizedImage()

        # TODO: a note to fix os.path dependency when transitioning to S3
        # and fix saving method from plt to boto3
        basename = self._upload.basename
        smallPath = os.path.join(self.media_root, basename+'_small.png')
        largePath = os.path.join(self.media_root, basename+'_large.png')

        # TODO: consider removing PIL dependency once trail detection is
        # implemented, if it is implemented via OpenCV
        img = Image.fromarray(np.uint8(normedImage*255))

        basewidth = 640
        wpercent = (basewidth / float(img.size[0]))

        hsize = int((float(img.size[1]) * float(wpercent)))
        img = img.resize((basewidth, hsize), Image.ANTIALIAS)

        img.save(smallPath)
        plt.imsave(largePath, normedImage)
