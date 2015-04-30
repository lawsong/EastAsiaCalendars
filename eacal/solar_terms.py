# -*- coding: utf-8 -*-

import ephem
import nutation
from math import pi

ABERR_CONST = (20.49552 / 3600. / 180. * pi)

twopi = pi * 2.
twelfth_pi = pi / 12.
twenty_fourth_pi = pi / 24.

degree = pi / 180.
arcminute = degree / 60.
arcsecond = arcminute / 60.
half_arcsecond = arcsecond / 2.
tiny = arcsecond / 360.


_sun = ephem.Sun()                    # used for computing equinoxes


def get_ap_hlon(mj, nutation_dpsi=None):
    _sun.compute(mj)
    if nutation_dpsi is None: nutation_dpsi = nutation.nutation(mj)[1]
    ap_hlon = _sun.hlon + nutation_dpsi - ABERR_CONST + pi
    if ap_hlon < 0.0:
        ap_hlon += twopi
    elif ap_hlon > twopi:
        ap_hlon -= twopi
    return ephem.degrees(ap_hlon)

def converge(d, deg):

    def get_diff(d, deg, nutation_dpsi=None):
        diff = float(deg) * degree - get_ap_hlon(d, nutation_dpsi)
        if diff > pi:
            diff -= twopi
        elif diff < -pi:
            diff += twopi
        return diff

    # 視黄経の差を利用して、10秒未満まで詰めていく
    for i in range(100):
        diff = get_diff(d, deg)
        if abs(diff) < ephem.degrees('0:00:01'):
            break
        d = d + 365.25 * diff / twopi  # 視黄経との差の値によってdを更新

    # nutationを固定し、二分法によってdiffの正負が逆転する箇所を特定
    nutation_dpsi = nutation.nutation(d)[1]
    d0, d1 = d-ephem.degrees('0:05:00'), d+ephem.degrees('0:05:00')
    f0, f1 = get_diff(d0, deg, nutation_dpsi), get_diff(d1, deg, nutation_dpsi)
    if f0 * f1 > 0.:
        print "warning: f0=%f, f1=%f" % (f0, f1)
        sys.exit(0)

    for i in range(20):  # limits the iteration number to 20.
        
        dn = (d0 + d1) / 2.
        fn = get_diff(dn, deg, nutation_dpsi)

        if fn * f0 > 0.:  # 中間点は左側と同じ符号 -> 右側に詰める
            d0 = dn
            f0 = get_diff(d0, deg, nutation_dpsi)
        elif fn * f1 > 0.:  # 中間点は右側と同じ符号 -> 右側に詰める
            d1 = dn
            f1 = get_diff(d1, deg, nutation_dpsi)
        elif fn == 0:
            return ephem.date(dn)
        else:
            print "warning"
            sys.exit(0)

    return ephem.Date((d0*abs(f1)+d1*abs(f0))/(abs(f0) + abs(f1)))


def solar_term_finder(mj, n, reverse=False):
    
    offset = n * twelfth_pi
    d0 = ephem.Date(mj)
    motion = -twopi if reverse else twopi

    angle_to_cover = motion - (get_ap_hlon(d0) - offset) % motion
    if abs(angle_to_cover) < tiny:
        angle_to_cover = motion
    d = d0 + 365.25 * angle_to_cover / twopi
    return converge(d, n * 15)


def solar_term_finder_deg(mj, deg, reverse=False):

    offset = deg * degree
    d0 = ephem.Date(d0)
    motion = -twopi if reverse else twopi

    angle_to_cover = motion - (get_ap_hlon(d0) - offset) % motion
    if abs(angle_to_cover) < tiny:
        angle_to_cover = motion
    d = d0 + 365.25 * angle_to_cover / twopi
    return converge(d, deg)


def get_annual_solar_terms(year, boundary_previous=False, boundary_following=False):

    ref = ephem.previous_winter_solstice(str(year)) + 0.01

    result = []
    for j in range(24):
        i = (j - 5) % 24
        d = solar_term_finder(ref, i).datetime()
        result.append((i, d))

    return result