#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  test_plot.py
#
#  Copyright 2017 Bruno S <bruno@oac.unc.edu.ar>
#
# This file is part of ProperImage (https://github.com/toros-astro/ProperImage)
# License: BSD-3-Clause
# Full Text: https://github.com/toros-astro/ProperImage/blob/master/LICENSE.txt
#

"""
Pytest configuration

Written by Bruno SANCHEZ, JB Cabral

PhD of Astromoy - UNC
bruno@oac.unc.edu.ar

Instituto de Astronomia Teorica y Experimental (IATE) UNC
Cordoba - Argentina Of 301
"""


# =============================================================================
# IMPORTS
# =============================================================================

import numpy as np

import pytest

from properimage import single_image as s, simtools


# =============================================================================
# CONSTANTS
# =============================================================================

# FIX the random state
random = np.random.RandomState(42)


# =============================================================================
# FIXTURES
# =============================================================================


@pytest.fixture
def random_simage():
    pixel = random.random((128, 128)) * 5.0
    # Add some stars to it
    star = [[35, 38, 35], [38, 90, 39], [35, 39, 34]]
    for i in range(25):
        x, y = random.randint(120, size=2)
        pixel[x : x + 3, y : y + 3] = star

    mask = random.randint(2, size=(128, 128))
    for i in range(10):
        mask = mask & random.randint(2, size=(128, 128))

    img = s.SingleImage(pixel, mask)

    return img


@pytest.fixture
def random_4psf_simage():

    frames = []
    for theta in [0, 45, 105, 150]:
        image_seed = int(random.rand() * 1000)

        N = 512  # side
        X_FWHM = 5 + 5.5 * theta / 180
        Y_FWHM = 5
        t_exp = 5
        max_fw = max(X_FWHM, Y_FWHM)

        x = random.randint(low=6 * max_fw, high=N - 6 * max_fw, size=80)
        y = random.randint(low=6 * max_fw, high=N - 6 * max_fw, size=80)
        xy = [(x[i], y[i]) for i in range(80)]

        SN = 30.0  # SN para poder medir psf
        weights = list(np.linspace(10, 1000.0, len(xy)))
        m = simtools.delta_point(N, center=False, xy=xy, weights=weights)
        im = simtools.image(
            m,
            N,
            t_exp,
            X_FWHM,
            Y_FWHM=Y_FWHM,
            theta=theta,
            SN=SN,
            bkg_pdf="gaussian",
            seed=image_seed,
        )
        frames.append(im + 100.0)

    frame = np.zeros((1024, 1024))
    for j in range(2):
        for i in range(2):
            frame[i * 512 : (i + 1) * 512, j * 512 : (j + 1) * 512] = frames[
                i + 2 * j
            ]

    return s.SingleImage(frame)
