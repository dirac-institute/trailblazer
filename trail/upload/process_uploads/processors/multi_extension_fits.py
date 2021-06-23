"""
A class that attempts to, as generically as possible, process FITS files with
multiple extensions.
"""


import matplotlib.pyplot as plt

from astropy.io.fits import ImageHDU
from astropy.io.fits.hdu.image import PrimaryHDU
from astropy.io.fits.hdu.compressed import CompImageHDU

from upload.process_uploads.fits_processor import FitsProcessor
from upload.models import Thumbnails


__all__ = ["MultiExtensionFits", ]


class MultiExtensionFits(FitsProcessor):

    name = "MultiExtensionFits"
    priority = 1

    def __init__(self, uploadInfo, uploadedFile):
        super().__init__(uploadInfo, uploadedFile)
        self.exts = []
        for hdu in self.hdulist:
            if self._isImageLikeHDU(hdu):
                self.exts.append(hdu)

    @staticmethod
    def _isImageLikeHDU(hdu):
        if not any((isinstance(hdu, CompImageHDU), isinstance(hdu, PrimaryHDU),
                    isinstance(hdu, ImageHDU))):
            return False

        # People store all kind of stuff even in ImageHDUs, let's make sure we
        # don't crash the server by saving 120k x 8000k table disguised as an
        # image (I'm looking at you SDSS!)
        if hdu.data is None:
            return False

        if len(hdu.data.shape) != 2:
            return False

        if hdu.shape[0] > 6000 or hdu.shape[1] > 6000:
            return False

        return True

    @classmethod
    def canProcess(cls, uploadedFile, returnHdulist=False):
        canProcess, hdulist = super().canProcess(uploadedFile, returnHdulist=True)
        canProcess = canProcess and cls._isMultiExtFits(hdulist)
        if returnHdulist:
            return canProcess, hdulist
        return canProcess

    def standardizeWcs(self):
        standardizedWcs = []
        for i, ext in enumerate(self.exts):
            standardizedWcs.append(self.standardizer.standardizeWcs(hdu=ext))
        return standardizedWcs

    def createThumbnails(self):
        thumbs = []
        for i, ext in enumerate(self.exts):
            large, small = self._createThumbnails(self.uploadedFile.basename + f"_ext{i}",
                                                  ext.data)
            self._storeThumbnail(large)
            self._storeThumbnail(small)
            thumbs.append(Thumbnails(large=large["savepath"], small=small["savepath"]))

        return thumbs
