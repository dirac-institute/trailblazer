"""
Class that facilitates header metadata translation for Las Cumbres Observatory.
"""

from datetime import datetime, timezone

from upload.process_uploads.header_standardizer import HeaderStandardizer
from upload.models import Metadata


__all__ = ["LasCumbresStandardizer", ]


class LasCumbresStandardizer(HeaderStandardizer):

    name = "las_cumbres_standardizer"
    priority = 1

    def __init__(self, header, **kwargs):
        super().__init__(header, **kwargs)

    @classmethod
    def canStandardize(self, header, **kwargs):
        origin = header.get("ORIGIN", False)
        if origin and "LCOGT" in origin.upper():
            return True
        return False

    def standardizeMetadata(self):
        # TODO: Fix datetimes
        # There is a timesys key but I have no idea how to generically instantiate
        # timezone aware datetime and astropy Time seems not to work well with
        # Django - the astrometadata is also broken!
        date = self.header["DATE"]
        utstart = self.header["UTSTART"]
        utstop = self.header["UTSTOP"]

        if self.header["TIMESYS"] == "UTC":
            tzinfo = timezone.utc
        else:
            raise ValueError("Can not recognize time scale system that is used?")

        startDatetime = datetime.strptime(date+"T"+utstart, "%Y-%m-%dT%H:%M:%S.%f")
        endDatetime = datetime.strptime(date+"T"+utstop, "%Y-%m-%dT%H:%M:%S.%f")
        startDatetime = startDatetime.replace(tzinfo=tzinfo)
        endDatetime = endDatetime.replace(tzinfo=tzinfo)

        # TODO: implement this lookup: https://arxiv.org/pdf/1305.2437.pdf
        # GP is essentially SDSS g filter, also figure out if filter none is
        # actually empyt or is there an actual fitler?
        meta = Metadata(
            obs_lon=self.header["LONGITUD"],
            obs_lat=self.header["LATITUDE"],
            obs_height=self.header["HEIGHT"],
            datetime_begin=startDatetime.isoformat(),
            datetime_end=endDatetime.isoformat(),
            telescope=self.header["TELESCOP"],
            instrument=self.header["INSTRUME"],
            science_program=self.header["PROPID"],
            exposure_duration=self.header["EXPTIME"],
            filter_name=self.header["FILTER"]
        )

        return meta
