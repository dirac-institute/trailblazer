"""
Class for processing calibrated FITS files produced by Vera C. Rubin Science
Pipelines.

Images processed by Rubin do *not* store the entire focal plane worth of data
in their FITS files, but only a single CCD image, alongside a mask and a
variance plane data.

We don't want to process variance or mask planes.
"""

from upload.process_uploads.processors import MultiExtensionFits


__all__ = ["RubinCalexpFits", ]


class RubinCalexpFits(MultiExtensionFits):

    name = "RubinCalexpFits"
    priority = 2

    def __init__(self, upload):
        super().__init__(upload)
        # this is the only image header
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
