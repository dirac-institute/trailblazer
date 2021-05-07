"""
Classes that facilitate processing of an FITS file.
"""


import os.path
from abc import ABC, abstractmethod

import numpy as np
from PIL import Image
import matplotlib.pyplot as plt

import astropy.visualization as aviz
from astropy.io import fits
from astropy.io.fits import ImageHDU
from astropy.io.fits.hdu.image import PrimaryHDU
from astropy.io.fits.hdu.compressed import CompImageHDU

from django.db import transaction

from upload.models import Frame
from upload.process_uploads.upload_processor import UploadProcessor
from upload.process_uploads.header_standardizer import HeaderStandardizer


__all__ = ["FitsProcessor", "SingleExtensionFits", "MultiExtensionFits"]


class FitsProcessor(UploadProcessor):
    """Suppports processing of a single FITS file.

    An upload is determined to be a FITS file if its extensions ends on one
    of the allowed extensions found in `extensions`.

    Parameters
    ----------
    upload : `tmpfile.TemporaryUploadedFileWrapper`
            Uploaded file.
    """

    #name = "FitsProcessor"
    #"""Processor's name."""

    extensions = [".fit", ".fits", ".fits.fz"]
    """File extensions this processor can handle."""

    def __init__(self, upload):
        super().__init__(upload)
        self.hdulist = fits.open(self._upload.tmpfile.temporary_file_path())
        self.isMultiExt = len(self.hdulist) > 1

    @staticmethod
    def _isImageLikeHDU(hdu):
        if not any((isinstance(hdu, CompImageHDU),
                    isinstance(hdu, PrimaryHDU),
                    isinstance(hdu, ImageHDU))):
            return False

        # Lets be reasonable, here - people store all kind of stuff even in
        # ImageHDUs, let's make sure we don't crash the server by saving 120k x
        # 8000k table disguised as an image (I'm looking at you SDSS!)
        if hdu.data is None:
            return False

        if len(hdu.data.shape) != 2:
            return False

        if hdu.shape[0] > 6000 or hdu.shape[1] > 6000:
            return False

        return True

    @staticmethod
    def _isMultiExtFits(hdulist):
        """Returns `True` when given HDUList contains more than 1 HDU.

        Parameters
        ----------
        hdulist : `astropy.io.fits.HDUList`
            An HDUList object.
        """
        return len(hdulist) > 1

    @classmethod
    def normalizeImage(cls, image):
        """Normalizes the image data to the [0,1] domain, using histogram
        equalization.

        Returns
        -------
        norm : `np.array`
            Normalized image.
        """
        # TODO: make things like these configurable (also see resize in
        # store_thumbnail)
        stretch = aviz.HistEqStretch(image)
        norm = aviz.ImageNormalize(image, stretch=stretch, clip=True)

        return norm(image)

    @classmethod
    def _createThumbnails(cls, filename, image, basewidth=640):
        """Creates a large and a small thumbnail images normalized to [0, 255]
        domain and their save locations.

        Parameters
        ----------
        filename : `str`
            Image filename.
        image : `numpy.array`
            Image
        basewidth : `int`, optional
            Width of the smaller thumbnail.

        Returns
        -------
        largeThumb : `dict`
            Dictionary containing the save location of the thumbnail,
            `savepath`, and the image, `thumb`.
        smallThumb : `dict`
            Dictionary containing the save location of the thumbnail,
            `savepath`, and the image, `thumb`.
        """
        normedImage = cls.normalizeImage(image)

        # TODO: a note to fix os.path dependency when transitioning to S3
        # and fix saving method from plt to boto3
        smallPath = os.path.join(cls.media_root, filename+'_small.jpg')
        largePath = os.path.join(cls.media_root, filename+'_large.jpg')

        # TODO: consider removing PIL dependency once trail detection is
        # implemented, if it is implemented via OpenCV
        normedImage = (normedImage.data*255).astype(np.uint8)
        # this is grayscale
        img = Image.fromarray(normedImage, "L")

        wpercent = (basewidth / float(img.size[0]))
        hsize = int((float(img.size[1]) * float(wpercent)))
        img = img.resize((basewidth, hsize), Image.ANTIALIAS)

        # img is PIL.Image object - simplify
        return ({"savepath": largePath, "thumb": normedImage},
                {"savepath": smallPath, "thumb": np.array(img)})

    @classmethod
    @abstractmethod
    def canProcess(cls, upload, returnHdulist=False):
        # docstring inherited from baseclass; TODO: check it's True
        canProcess, hdulist = False, None

        if upload.extension in cls.extensions:
            try:
                hdulist = fits.open(upload.tmpfile.temporary_file_path())
            except OSError:
                # OSError - file is corrupted, or isn't a fits
                # FileNotFoundError - upload is bad file, reraise!
                pass
            else:
                canProcess = True

        if returnHdulist:
            return canProcess, hdulist
        return canProcess

    @abstractmethod
    def standardizeWcs(self):
        """Standardize WCS data for each image-like header unit of the FITS.
        Standardized WCS are the Cartesian components of world coordinates of
        central and corner points on the image as projected onto a unit sphere.

        Returns
        -------
        standardizedWCS : `dict`
            A dictionary with standardized WCS keys and values.

        Notes
        -----
        Astropy is used to calculate on-sky coordinates, in degrees, of the
        center and of corner points. The center point is the center of the
        image as determined by image dimensions, determined directly or
        via header keywords, and the corner is taken to be the (0,0) pixel.
        Coordinates are then projected to a unit sphere, and the Cartesian
        components of the resulting projected points, as well as the distance
        between the center and corner coordiantes, are calculated.
        """
        # All Header operations are done by Standardizers. HeaderStandardizer
        # handles WCS standardization for all our data, so far.
        raise NotImplemented()

    @abstractmethod
    def standardizeHeaderMetadata(self):
        """Standardize selected header keywords from the primary header unit.
        Standardized header data are the observatory location, instrument
        description and time of observation.

        Returns
        -------
        standardizedHeaderMetadata : `dict`
            Dictionary containing the standardized FITS header keys.
        """
        # All Header operations are performed by Standardizers.
        raise NotImplemented()

    @abstractmethod
    def standardizeHeader(self, short=True):
        """Convenience function that standardizes the WCS and header metadata
        information and returns a dictionary of standardized metadata and wcs
        keys.

        Parameters
        ----------
        short : `bool`, optional
            When dealing with FITS files with multiple extensions will inject
            the shared header metadata into each standardized WCS dictionary.
            Otherwise, the long format is used, which separates the metadata
            and WCS data. Short format is used by default.

        Returns
        -------
        standardizedHeader : `dict`
            Dictionary containing standardized header metadata, per FITS file,
            and standardized WCS data, per image-like header in the FITS file.
        """
        raise NotImplemented()

    @abstractmethod
    def storeHeaders(self):
        """Convenience function that standardizes the WCS data and header
        metadata and inserts it into the database.
        """
        raise NotImplemented()

    @abstractmethod
    def storeThumbnails(self):
        """Convenience function that standardizes the WCS and header metadata
        and inserts it into the database.
        """
        raise NotImplemented()


class SingleExtensionFits(FitsProcessor):

    name = "SingleExtensionFits"

    def __init__(self, upload):
        super().__init__(upload)
        primary = self.hdulist["PRIMARY"].header
        self.standardizer = HeaderStandardizer.fromHeader(primary, filename=upload.filename)
        self.imageData = self.hdulist["PRIMARY"].data

    @classmethod
    def canProcess(cls, upload):
        canProcess, hdulist = super().canProcess(upload, returnHdulist=True)
        return canProcess and not cls._isMultiExtFits(hdulist)

    def standardizeWcs(self):
        return self.standardizer.standardizeWcs()

    def standardizeHeaderMetadata(self):
        return self.standardizer.standardizeMetadata()

    def standardizeHeader(self, short=True):
        standardizedWcs = {"wcs" : self.standardizeWcs()}
        standardizedMetadata = {"metadata" : self.standardizeHeaderMetadata()}
        if short:
            standardizedMetadata.update(standardizedWcs)
        else:
            standardizedMetadata = dict(standardizedMetadata["metadata"],
                                        **standardizedWcs["wcs"])
        return standardizedMetadata

    @transaction.atomic
    def storeHeaders(self, short=True):
        frame = Frame(**self.standardizeHeader(short=False))
        frame.save()

    def storeThumbnails(self):
        large, small = self._createThumbnails(self._upload.basename, self.imageData)
        plt.imsave(small["savepath"], small["thumb"])
        plt.imsave(large["savepath"], large["thumb"])


class MultiExtensionFits(FitsProcessor):

    name = "MultiExtensionFits"

    def __init__(self, upload):
        super().__init__(upload)

        # multiext fits usually encode metadata, which we use to resolve which
        # standardizer to use, in primary header. Primary header usually do not
        # contain an image. Only image headers contains valid WCSs. Images do
        # not, however, contain enough metadata to resolve which standardizer
        # to use. Just to be sure that this isn't a special multiext fits that
        # has data in primary (which I don't know how we would process atm...):
        self.primary = self.hdulist["PRIMARY"].header
        self.standardizer = HeaderStandardizer.fromHeader(self.primary,
                                                          filename=upload.filename)

        self.exts = []
        for hdu in self.hdulist:
            if self._isImageLikeHDU(hdu):
                self.exts.append(hdu)

    @classmethod
    def canProcess(cls, upload, returnHdulist=False):
        canProcess, hdulist = super().canProcess(upload, returnHdulist=True)
        canProcess = canProcess and cls._isMultiExtFits(hdulist)
        if returnHdulist:
            return canProcess, hdulist
        return canProcess

    def standardizeWcs(self):
        standardizedWcs = []
        for i, ext in enumerate(self.exts):
            standardizedWcs.append(self.standardizer.standardizeWcs(hdu=ext))
        return standardizedWcs

    def standardizeHeaderMetadata(self):
        return self.standardizer.standardizeMetadata()

    def standardizeHeader(self, short=True):
        standardizedWcs = {"wcs" : self.standardizeWcs()}
        standardizedMetadata = {"metadata" : self.standardizeHeaderMetadata()}

        if short:
            standardizedMetadata.update(standardizedWcs)
            return standardizedMetadata
        else:
            standardizedHeader = {}
            for wcs in standardizedWcs["wcs"].values():
                standardizedHeader[key] = dict(standardizedMetadata["metadata"],
                                               **wcs)
            return standardizedHeader

    def storeThumbnails(self):
        # TODO: I think a focal plane plot would be nicer, but that does need
        # more work than this
        for i, ext in enumerate(self.exts):
            large, small = self._createThumbnails(self._upload.basename + f"_ext{i}",
                                                  ext.data)
        plt.imsave(small["savepath"], small["thumb"])
        plt.imsave(large["savepath"], large["thumb"])

    @transaction.atomic
    def storeHeaders(self):
        # TODO: need to standardize the schema to be able to implement this
        pass
