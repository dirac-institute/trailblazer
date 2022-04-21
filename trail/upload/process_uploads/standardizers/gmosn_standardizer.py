"""
Class that facilitates header metadata translation for Gemini North instrument
"""

from datetime import datetime, timedelta

from astropy.time import Time

from upload.process_uploads.header_standardizer import HeaderStandardizer, StandardizeWcsException
from upload.models import Metadata, Wcs


__all__ = ["GmosnStandardizer", ]


class GmosnStandardizer(HeaderStandardizer):

    name = "gmosn_standardizer"
    priority = 2

    def __init__(self, header, **kwargs):
        super().__init__(header, **kwargs)

    @classmethod
    def canStandardize(self, header, **kwargs):
        lat = header.get("GEOLAT", False)
        if lat and 19.8200 == lat: return True
        return False

    def standardizeMetadata(self):

        # TODO: Fix datetimes
        # There is a timesys key but I have no idea how to generically instantiate
        # timezone aware datetime and astropy Time seems not to work well with
        # Django - the astrometadata is also broken!
        DATEOBS = self.header["DATE-OBS"]
        EXP = self.header["EXPTIME"]
        dec = DATEOBS.find('.')
        if dec != -1: date = DATEOBS[:dec]
        begin = datetime.fromisoformat(date)
        end = begin + timedelta(seconds= EXP)

        # TODO: filter out what is the filter standardization here?
        # After uploading, no "astrometry.net key" runtime err?
        meta = Metadata(
            obs_lon=self.header["GEOLON"],
            obs_lat=self.header["GEOLAT"],
            obs_height= 4213, #height in meters from official website
            datetime_begin=begin,
            datetime_end= end,
            telescope="Gemini North",
            instrument="GMOS", 
            exposure_duration=self.header["EXPTIME"],
            filter_name=self.header["FILTER"].strip()
        )

        return meta

    def standardizeWcs(self, **kwargs):
        # ignores any WCS information in the header and instead just sends it to astrometry.net to solve.
        # need to add a catch that catches the errors in astrometryNetSolver
        try:
            header, dimX, dimY = self._astrometryNetSolver(self._kwargs['filepath'])
        except ValueError and RuntimeError and TypeError as err:
            raise StandardizeWcsException("Failed to standardize WCS") from err
        return Wcs(**self._computeStandardizedWcs(header, dimX, dimY))
