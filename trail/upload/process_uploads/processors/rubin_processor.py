"""
Class for processing calibrated FITS files produced by Vera C. Rubin pipeline.
"""

from upload.process_uploads.processors.fits_processors import MultiExtensionFits
from upload.process_uploads.header_standardizer import HeaderStandardizer


class RubinCalexpFits(MultiExtensionFits):

    name = "RubinCalexpFits"

    def __init__(self, upload):
        super().__init__(upload)

        # Rubin flavored DECam processed images do *not* store the entire
        # focal plane worth of data in their FITS files, but only a single CCD
        # but alongside they store mask and variance as image-like data. We
        # don't want to process those images because, for us, they contain no
        # interesting data. 
        self.primary = self.hdulist["PRIMARY"].header
        self.standardizer = HeaderStandardizer.fromHeader(self.primary,
                                                          filename=upload.filename)
        # this is the image header
        self.exts = [self.hdulist[1], ]

    @classmethod
    def canProcess(cls, upload, returnHdulist=False):
        canProcess, hdulist = super().canProcess(upload, returnHdulist=True)
        # Unfortunately, there is no signature line left by Rubin pipeline,
        # so we are making a best guess estimate here.
        primary = hdulist["PRIMARY"].header
        isRubinProcessed = all(("ZTENSION" in primary,
                                "ZPCOUNT" in primary,
                                "ZGCOUNT" in primary,
                                "CCDNUM" in primary))
        canProcess = canProcess and isRubinProcessed

        if returnHdulist:
            return canProcess, hdulist
        return canProcess
