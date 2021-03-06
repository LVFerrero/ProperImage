#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  test_utils.py
#
#  Copyright 2018 Bruno S <bruno@oac.unc.edu.ar>
#
# This file is part of ProperImage (https://github.com/toros-astro/ProperImage)
# License: BSD-3-Clause
# Full Text: https://github.com/toros-astro/ProperImage/blob/master/LICENSE.txt
#

"""
test_utils module from ProperImage
for analysis of astronomical images

Written by Bruno SANCHEZ

PhD of Astromoy - UNC
bruno@oac.unc.edu.ar

Instituto de Astronomia Teorica y Experimental (IATE) UNC
Cordoba - Argentina

Of 301
"""

import os
import numpy as np
import tempfile

from astropy.io import fits

from properimage import utils

from .core import ProperImageTestCase

from properimage import simtools as sm


class UtilsBase(ProperImageTestCase):
    def setUp(self):
        print("setting up")
        self.tempdir = tempfile.mkdtemp()

        now = "2020-05-17T00:00:00.1234567"
        t = sm.Time(now)

        N = 1024
        SN = 15.0
        theta = 0
        xfwhm = 4
        yfwhm = 3
        weights = np.random.random(100) * 20000 + 10

        zero = 10  # for zero in [5, 10, 25]:
        filenames = []
        x = np.random.randint(low=30, high=900, size=100)
        y = np.random.randint(low=30, high=900, size=100)

        xy = [(x[i], y[i]) for i in range(100)]
        m = sm.delta_point(N, center=False, xy=xy, weights=weights)

        img_dir = os.path.join(self.tempdir, "zp_{}".format(zero))
        os.makedirs(img_dir)
        for i in range(4):
            im = sm.image(
                m,
                N,
                t_exp=2 * i + 1,
                X_FWHM=xfwhm,
                Y_FWHM=yfwhm,
                theta=theta,
                SN=SN,
                bkg_pdf="gaussian",
            )
            filenames.append(
                sm.capsule_corp(
                    im, t, t_exp=i + 1, i=i, zero=zero + i, path=img_dir
                )
            )

        self.filenames = filenames
        self.img = im
        self.img_masked = np.ma.MaskedArray(im, mask=np.zeros(im.shape))

    def testStoreImg_noStore(self):
        hdu = utils.store_img(self.img)
        self.assertIsInstance(hdu, fits.PrimaryHDU)

    def testStoreImg_Store(self):
        utils.store_img(self.img, path=os.path.join(self.tempdir, "tst.fits"))
        assert os.path.isfile(os.path.join(self.tempdir, "tst.fits"))

    def testStoreImg_noStoreMask(self):
        hdu = utils.store_img(self.img_masked)
        self.assertIsInstance(hdu, fits.HDUList)

    def testStoreImg_StoreMask(self):
        utils.store_img(
            self.img_masked, path=os.path.join(self.tempdir, "tst_mask.fits")
        )
        assert os.path.isfile(os.path.join(self.tempdir, "tst_mask.fits"))


class TestChunkIt(ProperImageTestCase):
    def setUp(self):
        self.data = np.random.random(20)

    def testChunks(self):
        for i in range(len(self.data)):
            chunks = utils.chunk_it(self.data, i + 1)
            self.assertIsInstance(chunks, list)

            flat_list = [item for sublist in chunks for item in sublist]
            self.assertCountEqual(flat_list, list(self.data))
