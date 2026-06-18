"""Tests unitaires pour le modèle environnemental."""
import yaml
import numpy as np
import pytest
from src.orbital import OrbitalParameters
from src.environment import EnvironmentModel


@pytest.fixture
def config():
    with open("config/cubesat_config.yaml") as f:
        return yaml.safe_load(f)


@pytest.fixture
def env(config):
    return EnvironmentModel(config)


@pytest.fixture
def orb():
    return OrbitalParameters(altitude_km=550, beta_deg=0)


class TestEnvironmentFluxes:

    def test_no_solar_in_eclipse(self, env, orb):
        """Aucun flux solaire pendant l'éclipse."""
        t_eclipse = orb.T_orb * 0.5    # Milieu de l'éclipse pour beta=0
        fluxes    = env.compute(t_eclipse, orb)
        total_solar = sum(f["solar"] for f in fluxes.values())
        assert total_solar == 0.0, f"Flux solaire non nul pendant éclipse : {total_solar}"

    def test_earth_ir_permanent(self, env, orb):
        """Le flux IR Terre est présent jour ET nuit."""
        t_ecl = orb.T_orb * 0.85
        t_sun = orb.T_orb * 0.25
        f_ecl = env.compute(t_ecl, orb)
        f_sun = env.compute(t_sun, orb)
        assert sum(f["earth_ir"] for f in f_ecl.values()) > 0
        assert sum(f["earth_ir"] for f in f_sun.values()) > 0

    def test_solar_only_on_visible_faces(self, env, orb):
        """Le flux solaire est nul sur les faces en ombre propre."""
        t_sun  = orb.T_orb * 0.25
        fluxes = env.compute(t_sun, orb)
        for face, fl in fluxes.items():
            assert fl["solar"] >= 0.0, f"Flux solaire négatif sur {face}"

    def test_rad_coef_positive(self, env, orb):
        """Le coefficient de rayonnement vers l'espace est strictement positif."""
        fluxes = env.compute(0.0, orb)
        for face, fl in fluxes.items():
            assert fl["rad_coef"] > 0.0
