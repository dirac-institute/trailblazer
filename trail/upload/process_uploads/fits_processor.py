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
from django.db import transaction

from upload.process_uploads.upload_processor import UploadProcessor
from upload.process_uploads.header_standardizer import HeaderStandardizer
from upload.models import StandardizedHeader, Thumbnails


__all__ = ["FitsProcessor",]


class FitsProcessor(UploadProcessor):
    """Suppports processing of a single FITS file.

    An upload is determined to be a FITS file if its extensions ends on one
    of the allowed extensions found in `extensions`.

    Parameters
    ----------
    uploadInfo : `uploads.model.UploadInfo`
        Object containing the time and date of upload and originating IP.
    uploadedFile : `upload_wrapper.temporaryUploadedFileWrapper`
        Uploaded file.

    Attributes
    ----------
    hdulist : `astropy.io.fits.HDUList`
        All HDUs found in the FITS file
    primary : `astropy.io.fits.PrimaryHDU`
        The primary header, a single HDU from hdulist identifying itself as
        the primary header.
    standardizer : `upload.HeaderStandardizer`
        The header standardizer that identified itself as capable of
        standardizing the primary header.
    isMultiExt : `bool`
        True when the FITS file has a multi extension header.

    Notes
    -----
    It is not recommended to use the standardizer's methods directly. Instead
    use their counterparts from processors.

    The standardizer operates, most often, on the primary HDU which usually
    containts all of the required metadata. For some multi-extension headers,
    however, usually the WCS data is contextualized via the primary HDU and
    primary HDU itself does not contain all the data required. It is the
    perogative of the processors to pick which additional HDUs are needed and
    to run the standardizers in the appropriate context. Shortcutting this
    process can, therefore, result in unexpected results or errors.
    """

    extensions = [".fit", ".fits", ".fits.fz"]
    """File extensions this processor can handle."""

    def __init__(self, uploadInfo, uploadedFile):
        super().__init__(uploadInfo, uploadedFile)
        self.hdulist = fits.open(uploadedFile.tmpfile.temporary_file_path())
        self.primary = self.hdulist["PRIMARY"].header
        self.standardizer = HeaderStandardizer.fromHeader(self.primary,
                                                          filename=uploadedFile.filename)
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

        Parameters
        ----------
        image : `np.array`
            Image.

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
    def _storeThumbnail(cls, thumbnail, savepath=None, pil_kwargs={"quality":30}):
        """Stores a single thumbnail (as returned by `_createThumbnails`).

        Parameters
        ----------
        thumbnail : `dict` or `np.array`
            Either a dictionary containing `savepath` and `thumb` image or just
            the thumbnail image.
        savepath : `str`, optional
            If given thumbnail is just the image it is required to supply the
            save location of the thumbnail.
        pil_kwargs : `dict`, optional
            Arguments that will be passed to PIL when saving the thumbnail.
            Default: `{quality: 30}`
        """
        # this looks stupid now, but it centralizes the storing functionality
        # for easier later transition to S3, so it's a placeholder for now:
        if isinstance(thumbnail, dict):
            savePath = thumbnail["savepath"]
            thumb = thumbnail["thumb"]
        elif savepath is not None:
            thumb = thumbnail
            savePath = savepath
        else:
            raise ValueError("Expected a dict or an image and savepath, got "
                             f"thumbnail={thumbnail} and savepath={savepath} "
                             "instead.")
        plt.imsave(savePath, thumb, cmap="Greys", pil_kwargs=pil_kwargs)

    @classmethod
    @abstractmethod
    def canProcess(cls, uploadedFile, returnHdulist=False):
        # docstring inherited from UploadProcessor; TODO: check it's True
        canProcess, hdulist = False, None

        if uploadedFile.extension in cls.extensions:
            try:
                hdulist = fits.open(uploadedFile.tmpfile.temporary_file_path())
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

        Standardized WCS consists of the Cartesian components of central and
        corner pixels on the image, as projected onto a unit sphere, and their
        distance.

        Returns
        -------
        standardizedWCS : `upload.models.Wcs`
            Standardized WCS keys and values.

        Notes
        -----
        Astropy is used to calculate on-sky coordinates, in degrees, of the
        center and of corner points.
        The center point is the center of the image as determined by header
        `NAXIS` keys, when able, and directly from image dimensions otherwise.
        The corner is taken to be the (0,0) pixel.

        Coordinates are then projected to a unit sphere, and the Cartesian
        components of the resulting projected points, as well as the distance
        between the center and corner coordiantes, are calculated.
        """
        raise NotImplementedError()

    @abstractmethod
    def createThumbnails(self):
        """Create a small and a large thumbnail for each image-like extension
        in the FITS file.

        Returns
        -------
        thumbnails : `list[upload.model.Thumbnail]`
            A list of Thumbnail objects for each of the selected image-like
            HDUs.

        Note
        ----
        Due to the size of some FITS files the image data itself is promptly
        saved to their save locations in order to avoid out-of-memory errors.
        To create the images see `_createThumbnails` method.
        """
        raise NotImplementedError()

    def standardizeHeaderMetadata(self):
        """Standardize selected header keywords from the primary header unit.

        Returns
        -------
        standardizedHeaderMetadata : `upload.model.Metadata`
            Metadata object containing standardized values.
        """
        meta = self.standardizer.standardizeMetadata()

        # some standardizers construct their own names which we do not want to
        # override
        meta.processor_name = self.name
        if not meta.standardizer_name:
            meta.standardizer_name = self.standardizer.name

        return meta

    def standardizeHeader(self):
        """Convenience function that standardizes the WCS and header metadata.

        Returns
        -------
        standardizedHeader : `upload.models.StandardizedHeader`
            A dataclass containing the standardized header metadata and one or
            more standardized WCS. 
        """
        meta = self.standardizeHeaderMetadata()
        wcs = self.standardizeWcs()

        stdHeader = StandardizedHeader(metadata=meta)
        wcs = self.standardizeWcs()
        try:
            stdHeader.appendWcs(wcs)
        except ValueError:
            stdHeader.extendWcs(wcs)
        return stdHeader

    @transaction.atomic
    def process(self):
        """Process uploaded file by:
            * Standardizing header metadata,
            * standardizing all WCS from image-like headers,
            * creating thumbnails
            * inserting the new data into the database
        """
        # TODO: get some error handling here

        # Insert upload info into DB
        self.uploadInfo.save()

        # get the new metadata and set up the relationship between metadata and
        # UploadInfo, Relationship between Meta and WCS are set in stdHead.save
        standardizedHeader = self.standardizeHeader()
        standardizedHeader.metadata.upload_info = self.uploadInfo
        standardizedHeader.save()

        # Create thumbnails (their DB models and the files) and then set up
        # relationship between particular wcs data and thumbs; then insert them
        # TODO: I'm iffed how this is set here, maybe refactor?
        thumbnails = self.createThumbnails()
        if isinstance(thumbnails, Thumbnails):
            for wcs in standardizedHeader.wcs:
                thumbnails.wcs = wcs
            thumbnails.save()
        else:
            # probably good: if len(wcs) != len(thumbnails): raise Error
            for wcs, thumb in zip(standardizedHeader.wcs, thumbnails):
                thumb.wcs = wcs
            # TODO: figure out why this doesn't work in StandardizedHeader.save
            Thumbnails.objects.bulk_create(thumbnails)

        # lastly, don't forget to upload the original science data.
        self.uploadedFile.save()
