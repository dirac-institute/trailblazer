from datetime import datetime, timedelta, timezone

from upload.process_uploads.header_standardizer import HeaderStandardizer
from upload.models import Metadata

import re


__all__ = ["VattStandardizer", ]


class VattStandardizer(HeaderStandardizer):
    """
    Class that facilitates header metadata translation for the Vatican Observatory

    Parameters
    ----------
    header: 'astropy.io.fits.header.Header'
        The header file for the FITS image
    """

    name = "vatt_standardizer"
    priority = 1

    def __init__(self, header, **kwargs):
        super().__init__(header, **kwargs)

    @classmethod
    def canStandardize(self, header, **kwargs):
        """Determines whether standardizer can standardize a header file

        Parameters
        ----------
        header: 'astropy.io.fits.header.Header'
            FITS header file for image

        Returns
        -------
        can_standardize: 'bool'
            Whether standardizer can standardize
        """
        dewar = header.get("DEWAR", False)
        if dewar and dewar == 'vatt4k_dewar':
            return True
        return False

    def standardizeMetadata(self):
        """Standardizes metadata from header of the FITS file

        Returns
        -------
        metadata: 'upload.models.Metadata'
            The metadata
        """

        #The date and time are seperated in the header, I concatenate them together here
        DATE = self.header["DATE-OBS"]
        TIME = self.header["TIME-OBS"]
        DATEOBS = DATE + 'T' + TIME
        EXP = self.header["EXPTIME"]
        begin = datetime.strptime(DATEOBS, "%Y-%m-%dT%H:%M:%S.%f")
        begin = begin.replace(tzinfo=timezone.utc)
        end = begin + timedelta(seconds=EXP)

        expr = re.compile(r'Filter(.*)')
        comment = str(self.header['COMMENT']).split('\n')
        matches = [expr.match(line).groups()[0] for line in comment]
        if len(matches) == 1:
            FILTER = matches[0]
        else:
            FILTER = None
        
        meta = Metadata(
            obs_lon=-109.892107,#Longitude from google maps
            obs_lat=32.701328,#Latitude from google maps
            obs_height=self.header["ELEVAT"],
            datetime_begin=begin.isoformat(),
            datetime_end=end.isoformat(),
            #Some of the instrument data has a weird format
            #They begin with a =" and end with a ", the
            #indices get rid of those extra characters
            telescope=self.header["TELESCOP"][3:-1].strip(),
            instrument=self.header["INSTRUME"][3:-1].strip(),
            exposure_duration=self.header["EXPTIME"],
            filter = FILTER
        )

        return meta
