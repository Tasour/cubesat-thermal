"""Tests unitaires pour le modèle orbital."""
import numpy as np
import pytest
from src.orbital import OrbitalParameters, sun_vector_rtn, in_eclipse, R_EARTH


class TestOrbitalParameters:

    def test_period_550km(self):
        """La période orbitale à 550 km doit être ~95-96 minutes."""
        orb = OrbitalParameters(altitude_km=550, beta_deg=0)
        assert 94 * 60 < orb.T_orb < 97 * 60

    def test_no_eclipse_high_beta(self):
        """Beta = 90° → jamais d'éclipse."""
        orb = OrbitalParameters(altitude_km=550, beta_deg=90)
        assert orb.eclipse_fraction == 0.0

    def test_eclipse_fraction_zero_beta(self):
        """Beta = 0° → éclipse significative (~35%)."""
        orb = OrbitalParameters(altitude_km=550, beta_deg=0)
        assert 0.30 < orb.eclipse_fraction < 0.42

    def test_eclipse_fraction_increases_with_altitude(self):
        """Plus l'altitude est basse, plus les éclipses sont longues."""
        orb_low  = OrbitalParameters(altitude_km=400, beta_deg=0)
        orb_high = OrbitalParameters(altitude_km=700, beta_deg=0)
        assert orb_low.eclipse_fraction > orb_high.eclipse_fraction

    def test_sun_vector_is_unit(self):
        """Le vecteur Soleil doit être unitaire."""
        orb = OrbitalParameters(altitude_km=550, beta_deg=30)
        for t in [0, 100, 1000, 5000]:
            vec = sun_vector_rtn(t, orb)
            assert abs(np.linalg.norm(vec) - 1.0) < 1e-10

    def test_eclipse_consistent_with_fraction(self):
        """La fraction d'éclipse Monte-Carlo doit correspondre à la formule."""
        orb = OrbitalParameters(altitude_km=550, beta_deg=0)
        n   = 2000
        t_s = np.linspace(0, orb.T_orb, n)
        mc_frac = sum(in_eclipse(t, orb) for t in t_s) / n
        assert abs(mc_frac - orb.eclipse_fraction) < 0.02  # ±2%
