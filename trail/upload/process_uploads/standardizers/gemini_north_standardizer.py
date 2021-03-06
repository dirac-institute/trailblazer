"""
Class that facilitates header metadata translation for Gemini North instrument
"""

from datetime import datetime, timedelta, timezone

from upload.process_uploads.header_standardizer import HeaderStandardizer
from upload.models import Metadata


__all__ = ["GeminiNorthStandardizer", ]


class GeminiNorthStandardizer(HeaderStandardizer):

    name = "gemini_north_standardizer"
    priority = 1

    def __init__(self, header, **kwargs):
        super().__init__(header, **kwargs)

    @classmethod
    def canStandardize(self, header, **kwargs):
        lat = header.get("GEOLAT", False)
        if lat and 19.8200 == lat:
            return True
        return False

    def standardizeMetadata(self):
        DATEOBS = self.header["DATE-OBS"]
        EXP = self.header["EXPTIME"]
        begin = datetime.strptime(DATEOBS, "%Y-%m-%dT%H:%M:%S.%f")
        begin = begin.replace(tzinfo=timezone.utc)
        end = begin + timedelta(seconds=EXP)

        '''
        Gemini North has changed their CCD's over the years. Using their official
        website, we know that the EEV was the CCD used before October of 2011, the
        e2v DD was the CCD used between October 2011 and June 2014, and the Hamamatsu
        CCD has been in use since June of 2014. The following logic determines the
        CCD in use for the image at the time the image was taken.
        '''
        oct_string = "2011-10-01T00:00:00.0"
        october11 = datetime.strptime(oct_string, "%Y-%m-%dT%H:%M:%S.%f")
        october11 = october11.replace(tzinfo=timezone.utc)
        june_string = "2014-06-01T00:00:00.0"
        june14 = datetime.strptime(june_string, "%Y-%m-%dT%H:%M:%S.%f")
        june14 = june14.replace(tzinfo=timezone.utc)

        if begin < october11:
            instrument = "EEV"
        elif begin < june14:
            instrument = "e2v DD"
        else:
            instrument = "Hamamatsu"

        meta = Metadata(
            obs_lon=self.header["GEOLON"],
            obs_lat=self.header["GEOLAT"],
            obs_height=4213,  # height in meters from official website
            datetime_begin=begin.isoformat(),
            datetime_end=end.isoformat(),
            telescope="Gemini North",
            instrument=instrument,
            exposure_duration=self.header["EXPTIME"],
            filter_name=self.header["FILTER"].strip()
        )

        return meta
