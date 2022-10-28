"""
Class that facilitates header metadata translation for Las Cumbres Observatory.
"""

from datetime import datetime, timezone

from upload.process_uploads.header_standardizer import HeaderStandardizer
from upload.models import Metadata


__all__ = ["WhippleStandardizer", ]


class WhippleStandardizer(HeaderStandardizer):

    name = "whipple_standardizer"
    priority = 1

    def __init__(self, header, **kwargs):
        super().__init__(header, **kwargs)

    @classmethod
    def canStandardize(self, header, **kwargs):
        observat = header.get("OBSERVAT", False)
        if observat and "WHIPPLE" in observat.upper():
            return True
        return False

    def standardizeMetadata(self):
        startt = datetime.strptime(self.header["DATE-OBS"], "%Y-%m-%dT%H:%M:%S.%f%z")
        endt = datetime.strptime(self.header["DATE-END"], "%Y-%m-%dT%H:%M:%S.%f%z")
        startt = startt.astimezone(timezone.utc)
        endt = endt.astimezone(timezone.utc)

        # TODO: there are multiple different telescopes
        # at the Whipple Obs site, check if there are any particularities
        # (height specifically) and implement conditions to handle them
        # http://www.sao.arizona.edu/FLWO/whipple.html
        # This is the Ridge location height
        height = self.header.get("HEIGHT", None)
        if height is None:
            if "cecilia" in self.header["TELESCOP"].lower() or "ben" in self.header["TELESCOP"]:
                height = 1268.00
            else:
                raise RuntimeError(
                    "Unable to parse height of the instrument. Header does "
                    "not contain key HEIGHT or is not one of the supported "
                    "known instruments at Whipple Observatory.")

        meta = Metadata(
            obs_lon=self.header["LONGITUD"],
            obs_lat=self.header["LATITUDE"],
            obs_height=height,
            datetime_begin=startt,
            datetime_end=endt,
            telescope=self.header["TELESCOP"],
            instrument=self.header["INSTRUME"],
            science_program=f"{self.header['ORIGIN']} {self.header['OBSID']}",
            exposure_duration=self.header["EXPTIME"],
            filter_name=self.header["FILTER"]
        )

        return meta
