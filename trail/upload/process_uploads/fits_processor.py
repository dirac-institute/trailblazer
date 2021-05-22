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

from upload.process_uploads.upload_processor import UploadProcessor
from upload.process_uploads.header_standardizer import HeaderStandardizer


__all__ = ["FitsProcessor",]


class FitsProcessor(UploadProcessor):
    """Suppports processing of a single FITS file.

    An upload is determined to be a FITS file if its extensions ends on one
    of the allowed extensions found in `extensions`.

    Parameters
    ----------
    upload : `upload_wrapper.TemporaryUploadedFileWrapper`
            Uploaded file.
    """

    extensions = [".fit", ".fits", ".fits.fz"]
    """File extensions this processor can handle."""

    def __init__(self, upload):
        super().__init__(upload)
        self.hdulist = fits.open(self._upload.tmpfile.temporary_file_path())
        self.primary = self.hdulist["PRIMARY"].header
        self.standardizer = HeaderStandardizer.fromHeader(self.primary,
                                                          filename=upload.filename)
        self.isMultiExt = len(self.hdulist) > 1

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
    def standardizeHeader(self):
        """Convenience function that standardizes the WCS and header metadata
        information and returns a dictionary of standardized metadata and wcs
        keys.

        Returns
        -------
        standardizedHeader : `dict`
            Dictionary containing standardized header metadata, per FITS file,
            and standardized WCS data, per image-like header in the FITS file.
        """
        return {"metadata": self.standardizeHeaderMetadata(),
                "wcs": self.standardizeWcs()}

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
