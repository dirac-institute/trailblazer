"""
Class that facilitates header metadata translation for MOA-II instrument
"""

from datetime import datetime, timezone

from astropy.time import Time

from upload.process_uploads.header_standardizer import HeaderStandardizer


__all__ = ["MoaStandardizer", ]


class MoaStandardizer(HeaderStandardizer):

    name = "moa_standardizer"
    priority = 1

    def __init__(self, header, **kwargs):
        super().__init__(header, **kwargs)

    @classmethod
    def canStandardize(self, header, **kwargs):
        obstel = header.get("OBSTEL", False)
        if obstel and "MOA" in obstel.upper():
            return True
        return False

    def standardizeMetadata(self):
        standardizedKeys = {}

        standardizedKeys["obs_lon"] = self.header["LOGITUD"]
        standardizedKeys["obs_lat"] = self.header["LATITUD"]
        standardizedKeys["obs_height"] = self.header["HEIGHT"]

        standardizedKeys["telescope"] = self.header["OBSTEL"].strip()
        standardizedKeys["instrument"] = self.header["CAMERA"].strip()

        run = self.header["RUN"].strip()
        field = self.header["FIELD"].strip()
        filter = self.header["COLOUR"].strip()
        chip = self.header["CHIP"]
        standardizedKeys["science_program"] = f"{run}-{field}-{filter}-{chip}"

        # TODO: Fix datetimes
        # There is a timesys key but I have no idea how to generically instantiate
        # timezone aware datetime and astropy Time seems not to work well with
        # Django - the astrometadata is also broken!
        if "UTC" in self.header["TIMESYS"].upper():
            tzinfo = timezone.utc
        else:
            raise ValueError("Can not recognize time scale system that is used?")

        jdstart = Time(self.header["JDSTART"], format="jd", scale="utc")
        jdstart = jdstart.utc.datetime
        jdstart = jdstart.replace(tzinfo=tzinfo)
        standardizedKeys["datetime_begin"] = jdstart.isoformat()

        jdend = Time(self.header["JDSTART"], format="jd", scale="utc")
        jdend = jdend.utc.datetime
        jdend = jdend.replace(tzinfo=tzinfo)
        standardizedKeys["datetime_end"] = jdend.isoformat()

        standardizedKeys["exposure_duration"] = self.header["EXPTIME"]

        # TODO: filter out what is the filter standardization here
        standardizedKeys["physical_filter"] = self.header["COLOUR"].strip()

        return standardizedKeys

    def standardizeWcs(self, **kwargs):
        # no matter how hard I try, I do not understand how it would ever be
        # possible to extract WCS data out of this header. That entire header
        # is nonsense...
        standardizedWcs = {}
        standardizedWcs["wcs_radius"] = -999.999
        standardizedWcs["wcs_center_x"] = -999.999
        standardizedWcs["wcs_center_y"] = -999.999
        standardizedWcs["wcs_center_z"] = -999.999
        standardizedWcs["wcs_corner_x"] = -999.999
        standardizedWcs["wcs_corner_y"] = -999.999
        standardizedWcs["wcs_corner_z"] = -999.999

        return standardizedWcs
