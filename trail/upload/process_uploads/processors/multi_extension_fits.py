"""
A class that attempts to, as generically as possible, process FITS files with
multiple extensions.
"""


from django.db import transaction
import matplotlib.pyplot as plt

from astropy.io.fits import ImageHDU
from astropy.io.fits.hdu.image import PrimaryHDU
from astropy.io.fits.hdu.compressed import CompImageHDU

from upload.process_uploads.fits_processor import FitsProcessor
from upload.models import Metadata, Wcs


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

    def standardizeHeaderMetadata(self):
        return self.standardizer.standardizeMetadata()

    def storeThumbnails(self):
        for i, ext in enumerate(self.exts):
            large, small = self._createThumbnails(self.uploadedFile.basename + f"_ext{i}",
                                                  ext.data)
        plt.imsave(small["savepath"], small["thumb"])
        plt.imsave(large["savepath"], large["thumb"])

    @transaction.atomic
    def storeHeaders(self):
        header = self.standardizeHeader()

        self.uploadInfo.save()
        meta = Metadata(upload_info=self.uploadInfo, **header["metadata"])
        meta.save()

        wcs = [Wcs(metadata=meta, **ext) for ext in header["wcs"]]
        Wcs.objects.bulk_create(wcs)
