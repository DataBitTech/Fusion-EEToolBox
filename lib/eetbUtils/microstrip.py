#======================================================
# This software is released under the MIT license:
#
# MIT License
# 
# Copyright (c) 2025 Pal Szabo
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
#======================================================

"""
Microstrip transmission line calculator using Hammerstad and Jensen equations.

References:
    E. Hammerstad and O. Jensen, "Accurate Models for Microstrip Computer-Aided
    Design," 1980 IEEE MTT-S International Microwave Symposium Digest, pp. 407-409.
"""

import math


class Microstrip:
    """
    Computes microstrip parameters using the Hammerstad and Jensen closed-form
    synthesis and analysis equations.

    Coordinate convention
    ---------------------
    w  : trace width 
    t  : trace thickness
    h  : substrate height (between trace bottom and reference plane)
    er : relative permittivity (dielectric constant) of the substrate [-]

    Lenghts can use any unit, but it must be used consistently!
    """

    # ------------------------------------------------------------------
    # Construction
    # ------------------------------------------------------------------

    def __init__(self, er: float, h: float, t: float) -> None:
        """
        Parameters
        ----------
        er : Substrate relative permittivity (must be >= 1).
        h  : Substrate height (must be > 0).
        t  : Trace thickness (must be >= 0).
        """
        if er < 1.0:
            raise ValueError(f"Relative permittivity er must be >= 1, got {er}")
        if h <= 0.0:
            raise ValueError(f"Substrate height h must be > 0, got {h}")
        if t < 0.0:
            raise ValueError(f"Trace thickness t must be >= 0, got {t}")

        self.er = er
        self.h = h
        self.t = t

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _ur_u1(self, w: float) -> tuple[float, float]:
        """
        Compute the two normalised effective widths used by H&J:

        u1  = (w + Δw1) / h  — used for the impedance in free space (Z1)
        ur  = (w + Δw ) / h  — used for er_eff and the final Z0

        The thickness correction follows the Hammerstad & Jensen / Qucs form:

            Δw1 = (t/π) · ln(1 + 4e / (t/h · coth²(√(6.517 u))))
            Δw  = Δw1 · (1 + sech(√(er − 1))) / 2

        For t = 0 both corrections are zero and u1 = ur = w/h.
        """
        h  = self.h
        er = self.er
        t  = self.t
        u  = w / h

        if t == 0.0:
            return u, u

        t_norm = t / h

        coth_val = 1.0 / math.tanh(math.sqrt(6.517 * u))
        du1 = (t_norm / math.pi) * math.log(
            1.0 + 4.0 * math.e / (t_norm * coth_val ** 2)
        )

        sech_val = 1.0 / math.cosh(math.sqrt(er - 1.0))
        du = du1 * (1.0 + sech_val) / 2.0

        u1 = u + du1
        ur = u + du
        return ur, u1

    def _hammerstad_ab(self, u: float) -> tuple[float, float]:
        """
        Intermediate coefficients a(u) and b(er) from H&J.
        """
        er = self.er
        a = (
            1.0
            + math.log((u**4 + (u / 52.0) ** 2) / (u**4 + 0.432)) / 49.0
            + math.log(1.0 + (u / 18.1) ** 3) / 18.7
        )
        b = 0.564 * ((er - 0.9) / (er + 3.0)) ** 0.053
        return a, b

    def _hammerstad_zl(self, u: float) -> float:
        """Characteristic impedance for a homogeneous medium (H&J)."""
        Z0 = 120.0 * math.pi
        fu = 6.0 + (2.0 * math.pi - 6.0) * math.exp(-(30.666 / u) ** 0.7528)
        return Z0 / (2.0 * math.pi) * math.log(fu / u + math.sqrt(1.0 + (2.0 / u) ** 2))

    def _hammerstad_er(self, u: float, a: float, b: float) -> float:
        """Quasi-static effective permittivity (H&J)."""
        er = self.er
        return (er + 1.0) / 2.0 + (er - 1.0) / 2.0 * (1.0 + 10.0 / u) ** (-a * b)

    # ------------------------------------------------------------------
    # Public API – analysis (w → Z0, er_eff)
    # ------------------------------------------------------------------

    def effective_permittivity(self, w: float) -> float:
        """
        Compute the effective relative permittivity er_eff of the microstrip.

        Uses the Hammerstad & Jensen dispersion-free (quasi-static) formula,
        including the full thickness correction via coth/sech.

        Parameters
        ----------
        w : Trace width.

        Returns
        -------
        er_eff : Effective relative permittivity [-].
        """
        if w <= 0.0:
            raise ValueError(f"Trace width w must be > 0, got {w}")

        ur, u1 = self._ur_u1(w)
        zr = self._hammerstad_zl(ur)
        z1 = self._hammerstad_zl(u1)
        a, b = self._hammerstad_ab(ur)
        e   = self._hammerstad_er(ur, a, b)
        # thickness-corrected er_eff (Qucs / H&J eq.)
        er_eff = e * (z1 / zr) ** 2
        return er_eff

    def impedance(self, w: float) -> float:
        """
        Compute the characteristic impedance Z0 of the microstrip [Ω].

        Uses the Hammerstad & Jensen closed-form expression with the full
        coth/sech thickness correction.

        Parameters
        ----------
        w : Trace width.

        Returns
        -------
        Z0 : Characteristic impedance [Ω].
        """
        if w <= 0.0:
            raise ValueError(f"Trace width w must be > 0, got {w}")

        ur, u1 = self._ur_u1(w)
        zr = self._hammerstad_zl(ur)
        a, b = self._hammerstad_ab(ur)
        e   = self._hammerstad_er(ur, a, b)
        Z0  = zr / math.sqrt(e)
        return Z0

    # ------------------------------------------------------------------
    # Public API – synthesis (Z0 → w)
    # ------------------------------------------------------------------

    def width_from_impedance(
        self,
        Z0_target: float,
        tol: float = 1e-6,
        max_iter: int = 200,
    ) -> float:
        """
        Compute the trace width w that yields a target characteristic impedance.

        A closed-form initial estimate (Wheeler synthesis) is refined with
        Newton-Raphson iteration so that the result is consistent with the
        Hammerstad & Jensen analysis equations used elsewhere in this class.

        Parameters
        ----------
        Z0_target : Target characteristic impedance [Ω].
        tol       : Convergence tolerance on |ΔZ0| [Ω]  (default 1 nΩ).
        max_iter  : Maximum Newton-Raphson iterations (default 200).

        Returns
        -------
        w : Trace width.
        """
        if Z0_target <= 0.0:
            raise ValueError(f"Target impedance must be > 0, got {Z0_target}")

        er = self.er
        h = self.h

        # ---- Wheeler closed-form initial guess --------------------------------
        A = (Z0_target / 60.0) * math.sqrt((er + 1.0) / 2.0) + (
            (er - 1.0) / (er + 1.0)
        ) * (0.23 + 0.11 / er)

        B = 377.0 * math.pi / (2.0 * Z0_target * math.sqrt(er))

        # Narrow-strip approximation (u < 2)
        u_narrow = 8.0 * math.exp(A) / (math.exp(2.0 * A) - 2.0)
        # Wide-strip approximation (u >= 2)
        u_wide = (
            2.0 / math.pi
            * (
                B
                - 1.0
                - math.log(2.0 * B - 1.0)
                + ((er - 1.0) / (2.0 * er)) * (math.log(B - 1.0) + 0.39 - 0.61 / er)
            )
        )

        u0 = u_narrow if u_narrow < 2.0 else u_wide
        w = max(u0 * h, 1e-15)  # guard against non-positive start

        # ---- Newton-Raphson refinement ----------------------------
        for _ in range(max_iter):
            Z_cur = self.impedance(w)
            dZ = Z_cur - Z0_target

            if abs(dZ) < tol:
                break

            # Numerical derivative dZ/dw
            dw = w * 1e-6 if w > 0 else 1e-12
            dZdw = (self.impedance(w + dw) - Z_cur) / dw

            if dZdw == 0.0:
                break

            w -= dZ / dZdw
            w = max(w, 1e-15)   # keep positive

        return w


# ---------------------------------------------------------------------------
# Module-level convenience functions
# ---------------------------------------------------------------------------

def analyze(er: float, h: float, t: float, w: float) -> dict[str, float]:
    """
    Return a dict with ``er_eff`` and ``Z0`` for the given geometry.

    Parameters
    ----------
    er : Substrate relative permittivity.
    h  : Substrate height.
    t  : Trace thickness.
    w  : Trace width.
    """
    ms = Microstrip(er=er, h=h, t=t)
    return {
        "w":      w,
        "er_eff": ms.effective_permittivity(w),
        "Z0":     ms.impedance(w),
    }


def synthesize(
    er: float, h: float, t: float, Z0_target: float
) -> dict[str, float]:
    """
    Return a dict with ``w``, ``er_eff`` and ``Z0`` for the target impedance.

    Parameters
    ----------
    er        : Substrate relative permittivity.
    h         : Substrate height.
    t         : Trace thickness.
    Z0_target : Target characteristic impedance [Ω].
    """
    ms = Microstrip(er=er, h=h, t=t)
    w = ms.width_from_impedance(Z0_target)
    return {
        "w":      w,
        "er_eff": ms.effective_permittivity(w),
        "Z0":     ms.impedance(w),
    }


# ---------------------------------------------------------------------------
# Quick self-test
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    # Typical FR-4 stackup: er=4.3, h=0.2 mm, t=35 µm (1 oz copper)
    er, h, t = 4.3, 0.200, 35e-3  # Note: t is now in mm

    print("=" * 55)
    print("Hammerstad & Jensen Microstrip Calculator")
    print("=" * 55)
    print(f"Substrate:  er={er},  h={h:.3f} mm,  t={t*1e3:.1f} µm")
    print()

    # Analysis examples
    for w_mm in (0.100, 0.200, 0.370, 0.500, 1.000):
        w = w_mm
        r = analyze(er, h, t, w)
        print(
            f"  w = {w_mm:.3f} mm  →  "
            f"Z0 = {r['Z0']:6.2f} Ω,  er_eff = {r['er_eff']:.4f}"
        )

    print()

    # Synthesis examples
    for Z0_target in (100.0, 75.0, 50.0, 40.0):
        r = synthesize(er, h, t, Z0_target)
        print(
            f"  Z0_target = {Z0_target:.1f} Ω  →  "
            f"w = {r['w']:.4f} mm  "
            f"(achieved Z0 = {r['Z0']:.4f} Ω,  er_eff = {r['er_eff']:.4f})"
        )

    print()
    print("Self-test complete.")
