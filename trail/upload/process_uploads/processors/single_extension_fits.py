"""
Class that attempts to, as generically as possible, to process FITS files with
single extension containing both the header and the image data.
"""


from django.db import transaction
import matplotlib.pyplot as plt

from upload.process_uploads.fits_processor import FitsProcessor
from upload.models import Frame


__all__ = ["SingleExtensionFits", ]


class SingleExtensionFits(FitsProcessor):

    name = "SingleExtensionFits"
    priority = 1

    def __init__(self, upload):
        super().__init__(upload)    
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
        plt.imsave(small["savepath"], small["thumb"], pil_kwargs={"quality": 10})
        plt.imsave(large["savepath"], large["thumb"], pil_kwargs={"quality": 30})
