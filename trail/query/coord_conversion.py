import numpy as np


def equatorial_to_unitsphere(ra, dec):
    """
    Convert ra and dec in radian from equtorial coordinate into cartesian coordinates.
    """
    x = np.cos(dec) * np.cos(ra)
    y = np.cos(dec) * np.sin(ra)
    z = np.sin(dec)

    return {"x": x, "y": y, "z": z}
