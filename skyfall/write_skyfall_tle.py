#!/usr/bin/env python3
"""
Write SKYFALL Walker Constellation as TLE File
===============================================
Converts SKYFALL's sgp4init parameters (72 orbits x 22 sats = 1,584 satellites)
into 3-line TLE format so CDN's generate.py can run the Dynamic Flipping algorithm
on the same constellation.

Satellite ordering matches SKYFALL exactly: sat_index = orbit_id * sat_per_orbit + sat_id
This ensures CDN satellite index k == SKYFALL satellite index k.

Usage
-----
    python write_skyfall_tle.py --output ../skyfall_walker.tle
    python write_skyfall_tle.py --output ../skyfall_walker.tle --epoch "2020-06-01 00:00:00"

Then run CDN:
    cd ../../dynamic-flipping-topology
    python generate.py --tle ../SKYFALL/skyfall_walker.tle \
                       --start "2020-06-01 00:00:00" \
                       --end   "2020-06-01 01:30:00" \
                       --step  15 \
                       --output ../SKYFALL/topology.json
"""

import argparse
import json
import math
import os
from datetime import datetime

import numpy as np

# ── TLE checksum ──────────────────────────────────────────────────────────────

def _tle_checksum(line: str) -> int:
    """Compute TLE line checksum (sum of digits + 1 for '-', mod 10)."""
    total = 0
    for ch in line[:-1]:
        if ch.isdigit():
            total += int(ch)
        elif ch == '-':
            total += 1
    return total % 10


# ── Mean motion from altitude ─────────────────────────────────────────────────

def _mean_motion_rev_per_day(altitude_km: float) -> float:
    """Kozai mean motion in revolutions/day for a circular orbit at given altitude."""
    GM = 3.9860044e14       # m^3/s^2
    R_earth = 6371393.0     # m
    r = R_earth + altitude_km * 1000.0
    n_rad_s = math.sqrt(GM / r**3)          # rad/s
    n_rev_day = n_rad_s * 86400 / (2 * math.pi)
    return n_rev_day


# ── Epoch as TLE day-of-year decimal ─────────────────────────────────────────

def _epoch_to_tle(epoch_dt: datetime) -> str:
    """
    TLE epoch field: 2-digit year + day-of-year with fractional day.
    e.g. 2020-06-01 00:00:00  →  '20153.00000000'
    """
    year_2digit = epoch_dt.year % 100
    day_of_year = epoch_dt.timetuple().tm_yday
    frac_day = (epoch_dt.hour * 3600 + epoch_dt.minute * 60 + epoch_dt.second) / 86400.0
    return f"{year_2digit:02d}{day_of_year + frac_day:012.8f}"


# ── Format a TLE float field ──────────────────────────────────────────────────

def _fmt_f8_4(val: float) -> str:
    """8-char field: sign + 7 chars, no leading space for positive."""
    return f"{val:8.4f}"


def _fmt_decimal_point(val: float, width: int = 10) -> str:
    """TLE decimal-point notation: '.NNNNNNNN' (no leading zero)."""
    s = f"{abs(val):.7f}"          # '0.0000123'
    s = s[1:]                       # '.0000123'
    sign = '-' if val < 0 else ' '
    return f"{sign}{s}"


# ── Build one TLE entry ───────────────────────────────────────────────────────

def make_tle(sat_num: int, name: str, epoch_str: str,
             raan_deg: float, incl_deg: float, mean_anomaly_deg: float,
             mean_motion_rev_day: float,
             bstar: float = 2.8098e-05,
             ecco: float = 0.001,
             argpo_deg: float = 0.0,
             rev_at_epoch: int = 0) -> tuple[str, str, str]:
    """
    Build a 3-line TLE (name, line1, line2) for a single satellite.
    Returns (name_line, line1, line2) each as a string without trailing newline.
    """
    # ── Line 1 ────────────────────────────────────────────────────────────────
    # Format: 1 NNNNNC NNNNNAAA NNNNN.NNNNNNNN +.NNNNNNNN +NNNNN-N +NNNNN-N N NNNNN
    sat_id_str = f"{sat_num:05d}"
    classification = 'U'
    intl_designator = f"00001{'A':>3}"    # placeholder designator

    # ndot (first derivative of mean motion): use small positive value
    ndot = 6.969196665e-13 * 86400**2 / (2 * math.pi)   # rev/day^2, near zero
    # bstar in TLE decimal notation: e.g. 2.8098e-5 → ' 28098-4'
    def _bstar_str(b: float) -> str:
        if b == 0:
            return ' 00000-0'
        exp = math.floor(math.log10(abs(b))) + 1
        mantissa = b / 10**exp
        mantissa_int = int(round(mantissa * 100000))
        sign = '-' if b < 0 else ' '
        exp_sign = '-' if exp < 0 else '+'
        return f"{sign}{abs(mantissa_int):05d}{exp_sign}{abs(exp):01d}"

    ndot_str = ' .00000000'   # negligible for our purposes

    line1_body = (
        f"1 {sat_id_str}{classification} {intl_designator} "
        f"{epoch_str} "
        f"{ndot_str} "
        f" 00000-0 "
        f"{_bstar_str(bstar)} "
        f"0 {rev_at_epoch:4d}"
    )
    # Pad/trim to 68 chars then append checksum
    line1_body = f"{line1_body:<68}"
    line1 = line1_body + str(_tle_checksum(line1_body + '0'))

    # ── Line 2 ────────────────────────────────────────────────────────────────
    # Format: 2 NNNNN NNN.NNNN NNN.NNNN NNNNNNN NNN.NNNN NNN.NNNN NN.NNNNNNNNNNNNNN
    ecco_str = f"{ecco:.7f}"[2:]   # strip '0.' → 7 digits
    line2_body = (
        f"2 {sat_id_str} "
        f"{incl_deg:8.4f} "
        f"{raan_deg % 360:8.4f} "
        f"{ecco_str} "
        f"{argpo_deg:8.4f} "
        f"{mean_anomaly_deg % 360:8.4f} "
        f"{mean_motion_rev_day:11.8f}"
        f"{rev_at_epoch:5d}"
    )
    line2_body = f"{line2_body:<68}"
    line2 = line2_body + str(_tle_checksum(line2_body + '0'))

    return name, line1, line2


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Generate TLE file for SKYFALL's Walker constellation",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples
--------
  python write_skyfall_tle.py --output ../skyfall_walker.tle
  python write_skyfall_tle.py --output ../skyfall_walker.tle --epoch "2020-06-01 00:00:00"

Then run CDN topology generator:
  cd ../../dynamic-flipping-topology
  python generate.py \\
      --tle ../SKYFALL/skyfall_walker.tle \\
      --start "2020-06-01 00:00:00" \\
      --end   "2020-06-01 01:30:00" \\
      --step  15 \\
      --output ../SKYFALL/topology.json
        """,
    )
    parser.add_argument("--output", default="../skyfall_walker.tle",
                        help="Output TLE file path (default: ../skyfall_walker.tle)")
    parser.add_argument("--config", default="../config.json",
                        help="SKYFALL config.json path (default: ../config.json)")
    parser.add_argument("--epoch", default="2020-06-01 00:00:00",
                        help="TLE epoch datetime, UTC (default: '2020-06-01 00:00:00')")
    args = parser.parse_args()

    # ── Load SKYFALL config ───────────────────────────────────────────────────
    with open(args.config) as f:
        cfg = json.load(f)
    altitude_km    = float(cfg["Altitude (km)"])
    num_of_orbit   = int(cfg["# of orbit"])
    sat_per_orbit  = int(cfg["# of satellites"])
    inclination_deg = float(cfg["Inclination"])
    F = 1   # phase factor (matches generate_lla.py)

    sat_num_total = num_of_orbit * sat_per_orbit
    mean_motion   = _mean_motion_rev_per_day(altitude_km)
    epoch_dt      = datetime.strptime(args.epoch, "%Y-%m-%d %H:%M:%S")
    epoch_str     = _epoch_to_tle(epoch_dt)

    print(f"Constellation: {num_of_orbit} orbits × {sat_per_orbit} sats = {sat_num_total} satellites")
    print(f"Altitude: {altitude_km} km  |  Inclination: {inclination_deg}°  |  Mean motion: {mean_motion:.8f} rev/day")
    print(f"Epoch: {args.epoch}")
    print(f"Writing → {args.output}")

    lines = []
    for i in range(num_of_orbit):
        raan_deg = i / num_of_orbit * 360.0
        for j in range(sat_per_orbit):
            # Exactly matches generate_lla.py lines 36-37
            mean_anomaly_deg = (j * 360.0 / sat_per_orbit +
                                i * 360.0 * F / sat_num_total) % 360.0
            sat_index = i * sat_per_orbit + j
            name = f"SKYFALL-{sat_index:04d}"

            name_line, line1, line2 = make_tle(
                sat_num        = sat_index + 1,   # TLE sat numbers are 1-based
                name           = name,
                epoch_str      = epoch_str,
                raan_deg       = raan_deg,
                incl_deg       = inclination_deg,
                mean_anomaly_deg = mean_anomaly_deg,
                mean_motion_rev_day = mean_motion,
            )
            lines.append(name_line)
            lines.append(line1)
            lines.append(line2)

    out_dir = os.path.dirname(args.output)
    if out_dir and not os.path.exists(out_dir):
        os.makedirs(out_dir)

    with open(args.output, 'w') as f:
        f.write('\n'.join(lines) + '\n')

    print(f"Done. Wrote {sat_num_total} TLE entries ({sat_num_total * 3} lines) to {args.output}")


if __name__ == "__main__":
    main()
