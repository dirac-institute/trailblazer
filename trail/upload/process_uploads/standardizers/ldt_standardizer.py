"""
Class that facilitates header metadata translation for Lowell Discovery Telescope
"""

from datetime import datetime, timedelta, timezone

from upload.process_uploads.header_standardizer import HeaderStandardizer
from upload.models import Metadata


__all__ = ["LdtStandardizer", ]


class LdtStandardizer(HeaderStandardizer):

    name = "lowell_discovery_telescope_standardizer"
    priority = 1

    def __init__(self, header, **kwargs):
        super().__init__(header, **kwargs)

    @classmethod
    def canStandardize(self, header, **kwargs):
        lat = header.get("GEOLAT", False)
        if lat and 34.7444 == lat:
            return True
        return False

    def standardizeMetadata(self):
        DATEOBS = self.header["DATE-OBS"]
        EXP = self.header["EXPTIME"]
        begin = datetime.strptime(DATEOBS, "%Y-%m-%dT%H:%M:%S.%f")
        begin = begin.replace(tzinfo=timezone.utc)
        end = begin + timedelta(seconds=EXP)


        #TODO: Find Height, Find Instrument
        meta = Metadata(
            obs_lon=self.header["GEOLON"],
            obs_lat=self.header["GEOLAT"],
            obs_height=0,  # height in meters from official website
            datetime_begin=begin.isoformat(),
            datetime_end=end.isoformat(),
            telescope="Lowell Discovery Telescope",
            instrument="",
            exposure_duration=self.header["EXPTIME"],
            filter_name=self.header["FILTER"].strip()
        )

        return meta
