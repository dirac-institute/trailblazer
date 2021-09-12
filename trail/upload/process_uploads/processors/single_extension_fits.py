"""
Class that attempts to, as generically as possible, to process FITS files with
single extension containing both the header and the image data.
"""


from upload.process_uploads.fits_processor import FitsProcessor
from upload.models import Thumbnails

__all__ = ["SingleExtensionFits", ]


class SingleExtensionFits(FitsProcessor):

    name = "SingleExtensionFits"
    priority = 1

    def __init__(self, uploadInfo, uploadedFile):
        super().__init__(uploadInfo, uploadedFile)
        self.imageData = self.hdulist["PRIMARY"].data

    @classmethod
    def canProcess(cls, uploadedFile):
        canProcess, hdulist = super().canProcess(uploadedFile, returnHdulist=True)
        return canProcess and not cls._isMultiExtFits(hdulist)

    def standardizeWcs(self):
        return self.standardizer.standardizeWcs()

    def createThumbnails(self):
        large, small = self._createThumbnails(self.uploadedFile.basename, self.imageData)
        thumb = Thumbnails(large=large["savepath"], small=small["savepath"])
        self._storeThumbnail(large["img"], savepath=thumb.largeAbsPath)
        self._storeThumbnail(small["img"], savepath=thumb.smallAbsPath)
        return thumb
