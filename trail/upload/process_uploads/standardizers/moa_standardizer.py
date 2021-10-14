"""
Class that facilitates header metadata translation for MOA-II instrument
"""

from datetime import timezone

from astropy.time import Time

from upload.process_uploads.header_standardizer import HeaderStandardizer, StandardizeWcsException
from upload.models import Metadata, Wcs


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
        run = self.header["RUN"].strip()
        field = self.header["FIELD"].strip()
        filter = self.header["COLOUR"].strip()
        chip = self.header["CHIP"]
        sciProg = f"{run}-{field}-{filter}-{chip}"

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

        jdend = Time(self.header["JDSTART"], format="jd", scale="utc")
        jdend = jdend.utc.datetime
        jdend = jdend.replace(tzinfo=tzinfo)

        # TODO: filter out what is the filter standardization here?
        meta = Metadata(
            obs_lon=self.header["LOGITUD"],
            obs_lat=self.header["LATITUD"],
            obs_height=self.header["HEIGHT"],
            datetime_begin=jdstart.isoformat(),
            datetime_end=jdend.isoformat(),
            telescope=self.header["OBSTEL"].strip(),
            instrument=self.header["CAMERA"].strip(),
            science_program=sciProg,
            exposure_duration=self.header["EXPTIME"],
            filter_name=self.header["COLOUR"].strip()
        )

        return meta

    def standardizeWcs(self, **kwargs):
        # ignores any WCS information in the header and instead just sends it to astrometry.net to solve.
        # need to add a catch that catches the errors in astrometryNetSolver
        try:
            header, dimX, dimY = self._astrometryNetSolver(self._kwargs['filepath'])
            wcs = Wcs(**self._computeStandardizedWcs(header, dimX, dimY))
        except ValueError and RuntimeError and TypeError as err:
            raise StandardizeWcsException("Failed to standardize WCS") from err
        return wcs
