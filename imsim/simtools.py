#!/usr/bin/env python
# -*- coding: utf-8 -*-
import numpy as np
import scipy as sp
from scipy import signal as sg
from scipy import stats


def Psf(N, FWHM):
    """Psf es una funcion que proporciona una matriz 2D con una gaussiana
    simétrica en ambos ejes. con N se especifica el tamaño en pixeles que
    necesitamos y con FWHM el ancho sigma de la gaussiana en pixeles"""
    a = np.zeros((N, N))
    mu = (N-1)/2.
    sigma = FWHM/2.
    for i in range(N-1):
        for j in range(N-1):
            a[i, j] = stats.norm.pdf(i, loc=mu, scale=sigma) * \
                       stats.norm.pdf(j, loc=mu, scale=sigma)
    return(a)


def _airy_func(rr, width, amplitude=1.0):
    """
   For a simple radially symmetric airy function, returns the value at a given
    (normalized) radius
    """
    return amplitude * (2.0 * sp.special.j1(rr/width) / (rr/width))**2


def airy_patron(N, width):
    """Esta funcion genera un patron de airy, en una matriz 2D
     el cual es la impronta
     del espejo del telescopio y sigue una relacion de

       sin(theta) = 1.22 (Lambda / D)

     donde theta es la distancia desde el centro del patron a el primer
     minimo del mismo, lambda es la longitud de onda de la radiacion que
     colecta el telescopio, y D es el diametro del objetivo del telescopio
     N es el tamaño de la matriz en pixeles
     width es el theta ya calculado. Es importante saber que este theta
     depende del CCD también, ya que esta construida la funcion en pixeles
    """
    mu = (N-1)/2.
    a = np.zeros((N, N))
    for i in range(N):
        for j in range(N):
            r_pix = np.sqrt((i-mu)**2 + (j-mu)**2)
            a[i, j] = _airy_func(r_pix, width)
    return(a)


def convol_gal_psf_fft(gal, a):
    """
    Esta funcion convoluciona dos matrices, a pesar de su nombre es una FFT
    para matrices 2D, y se usa con el patron de airy tambien

    convol_gal_psf_fft(gal, a)

    retorna la convolucion de gal x a, usando la misma forma matricial que gal.
    """
    b = sg.fftconvolve(gal, a, mode="same")
    return(b)


def pixelize(L, M):
    """
    Funcion que pixeliza una matriz, es decir reduce el tamaño de la matriz
    original, donde los nuevos pixeles son cuadrados de lado L, en
    unidades de pixeles de la imagen primitiva
    puede arrojar dos errores,
      * en caso que la matriz inicial no sea cuadrada
      * en caso de que los nuevos pixeles no puedan cubrir la matriz primitiva

    L es el lado del nuevo pixel
    M es la matriz a pixelar
    Retorna la matriz repixelizada
    """
    s = np.shape(M)
    if s[1] != s[0]:
        print("Bad array, NOT SQUARE")
        return
    elif np.mod(s[1], L) != 0:
        print("Bad new pixel size")
        return
    elif L == 1:
        return(M)
    else:
        m = s[1]/L
        M2 = np.zeros((m, m))  # initialize new matrix
        for i in range(0, s[1], L):
            for j in range(0, s[1], L):
                h = 0
                for k in range(0, L-1):
                    for n in range(0, L-1):
                        h = M[i+k, j+n] + h
                M2[i/L, j/L] = h
    return(M2)


def cielo(N, pdf='poisson', mean=1, std=None):
    """
    esta funcion arroja una matriz de lado N con los pixeles
    con valores random extraidos de una distribucion poisson o gaussiana con
    media mean, y varianza std**2
    """
    if pdf == 'poisson':
        # promedio cuentas del cielo=lam
        x = np.random.poisson(mean, (N, N)).astype(np.float32)
    elif pdf == 'gaussian':
        x = np.random.normal(mean, std, (N,N)).astype(np.float32)
    return(x)


def perfilsersic(r_e, I_e, n, r):
    """
    funcion que evalua a un dado radio r el valor de
    brillo correspondiente a un perfil de sersic
         r_e  :  Radio de escala
         I_e  :  Intensidad de escala
         n    :  Indice de Sersic
         r    :  Radio medido desde el centro en pixeles
    """
    b = 1.999*n - 0.327
    I_r = I_e * np.exp(-b*(((r/r_e)**(1/np.float(n)))-1))
    I_r = I_r/(I_e*np.exp(-b*(((0.0/r_e)**(1/np.float(n)))-1)))
    return(I_r)


def gal_sersic(N, n):
    """
    esta funcion genera una matriz 2D que posee en sus componentes
    un perfil de sersic centrado en la matriz cuadrada, con un tamaño N
    y que posee un indice de sersic n
    """
    gal = np.zeros((N, N))
    mu = (N-1)/2.       # calculo posicion del pixel central
    R_e = ((N-1)/6.)    # radio de escala, tomado como un
                        # sexto del ancho de la imagen
                        # para que la galaxia no ocupe toda la imagen
    for i in range(N-1):
        for j in range(N-1):
            r_pix = np.sqrt((i-mu)**2 + (j-mu)**2)
            if r_pix <= (4.5*R_e):
                gal[i, j] = perfilsersic(R_e, 10, n, r_pix)
            else:
                gal[i, j] = 0
    return(gal)


def incline2(gal, theta):
    """
    funcion que inclina una imagen, en donde theta = 90
    es una imagen face-on
    y theta = 0 es una imagen vista de canto
    """
    s = np.shape(gal)
    gal2 = np.zeros(s)
    for i in range(s[0]):
        for j in range(s[1]):
            # defino la nueva posicion del pixel
            x = i
            y = j*np.sin(theta)  # msen(theta)
            y_new = round(y)  # n mas cercano
            gal2[x, y_new + ((s[1]/2.)*(1-np.sin(theta)))] = gal[i, j]
    return(gal2)


def image(MF, N2, t_exp, FWHM, SN, bkg_pdf='poisson', std=None):
    """
    funcion que genera una imagen con ruido y seeing a partir
    de un master frame, y la pixeliza hasta tamaño N2

    Parametros
    ----------
    IMC : imagen Master
    FWHM : tamaño en pixeles del FWHM del seeing
    t_exp : tiempo exposicion de la imagen
    N2 : tamaño de la imagen final, pixelizada
    SN : es la relacion señal ruido con el fondo del cielo
    bkg_pdf : distribucion de probabilidad del ruido background
    std : en caso que bkg_pdf sea gaussian, valor de std
    """
    N = np.shape(MF)[0]
    PSF = Psf(64, FWHM)
    IM = convol_gal_psf_fft(MF, PSF)
    if N != N2:
        image = pixelize(N/N2, IM)
    else:
        image = IM

    b = np.max(image) #image[int(N2/2), int(N2/2)]
    if bkg_pdf == 'poisson':
        mean = (b/SN)**2.
        print 'mean = {}, b = {}, SN = {}'.format(mean, b, SN)
        C = cielo(N=N2, pdf=bkg_pdf, mean=mean)
    elif bkg_pdf == 'gaussian':
        mean = 0
        std = b/SN
        print 'mean = {}, std = {}, b = {}, SN = {}'.format(mean, std, b, SN)
        C = cielo(N=N2, pdf=bkg_pdf, mean=mean, std=std)
    F = C + image
    return(F)


def inyeccion(MF, JD, largo, d, phi_0, t_decay,
              x, y, zero_point, mag_pico, res):
    """
    funcion que inyecta en un master frame un transitorio simulado
    por ahora tan solo es una gaussiana, con
        MF     :   El nombre del master frame
        JD     :   La fecha de la imagen en dias julianos
        largo  :   Largo total de la serie temporal
        d      :   Tiempo cero en dias julianos de la serie temporal
        phi    :   Coeficiente entre 0 y 1, que marca en que porcentaje del
                   #largo total de dias de la serie (largo) el transitorio
                   #tiene su pico
        t_decay:   el valor en dias del sigma de la gaussiana del transitorio
        x      :   posicion en x del masterframe del transitorio
        y      :   posicion en y del masterframe del transitorio
        zero_point:el punto cero de la magnitud instrumental
        mag_pico:  la magnitud pico del transitorio
        res    :    El tamaño del patron de airy del telescopio
        JD varia entre d y d+largo
    """
    Air = airy_patron(32, res)
    dia_pico = d + (largo*phi_0)  # dia donde esta el pico gaussiano
    escala = t_decay              # escala en dias de la distribucion
    cuentas_pico = 10**((zero_point-mag_pico)/2.5)
    gau = cuentas_pico*stats.norm.pdf(JD, loc=dia_pico, scale=escala)
    s = np.shape(MF)
    transit = np.zeros(s)
    transit[x, y] = gau
    IM = convol_gal_psf_fft(transit, Air)
    return(MF + IM)


def delta_point(N, center=True, xy=None):
    """
    Function to create delta sources in a square NxN matrix.
    If center is True (default) it will locate a unique delta
    in the center of the image.
    Else it will need a xy list of positions where to put the deltas.

    Returns a NxN numpy array.

    Example:
    N = 100
    x = [np.random.randint(10, 80) for j in range(10)]
    y = [np.random.randint(10, 80) for j in range(10)]
    xy = [(x[i], y[i]) for i in range(10)]

    m = delta_point(N, center=False, xy=xy)
    """
    m = np.zeros(shape=(N, N))
    if center is False:
        for x, y in xy.__iter__():
            m[x, y] = 1.
    else:
        m[int(N/2), int(N/2)] = 1
    return(m)


def master_frame(N, n, theta, res):  # funcion generadora de Master Frame
    """
    los parametros son:
    N= tamaño en pixeles de la imagen High Resolution
    n = indice de sercic para la galaxia simulada
    res= resolucion del telescopio + camara dado en unidades
        de pixeles del tamaño del patron de
        airy sin(theta)=1.22*(lambda/D)
        es decir el theta ya calculado
    """
    counts = 1000
    IM = gal_sersic(N, n)
    alfa = (np.pi/180.0)*theta
    IMI = incline2(IM, alfa)
    Air = airy_patron(32, res)
    a = IMI[round(N/2-1), round(N/2)]
    IMI[round(N/5), round(N/5)] = 10*a    # estrella 1
    IMI[round(4*N/5), round(N/5)] = 20*a  # estrella 2
    IMI[round(N/5), round(4*N/5)] = 50*a  # estrella 3 (Mag=12)
    IMI[round(4*N/5), round(4*N/5)] = 100*a  # estrella 4
    IMI[round(2.5*N/5), round(4*N/5)] = 100*a  # estrella 5
    IMI[round(4*N/5), round(2.5*N/5)] = 100*a  # estrella 6
    # la estrella con 50*a debe ser magnitud 12
    # por lo que entonces zero_point=12+2.5*log10(50*a*counts)
    zero = 12+2.5*np.log10(IMI[round(N/5), round(4*N/5)]*counts)
    print(zero)
    IMC = convol_gal_psf_fft(counts*IMI, Air)
    return(IMC)


def set_generator(n, air, FWHM, theta, N, Ntot):
    """
    funcion que genera el set de imágenes
     necesita de los parametros del
    n      :       Indice de Sersic
    air    :       tamaño del patron de Airy
    FWHM   :       Tamaño del seeing
    theta  :       Angulo de inclinacion (90 == sin inclinacion)
    N      :       Tamaño de las imagenes en pixeles
    Ntot   :       Cantidad de epocas
    """
    # generar la master frame de donde salen las demas imagenes
    Master_F = master_frame(1024, n, theta, air)
    # bucle de generacion de fits.
    # a=Master_F[round(1024./2.-1),round(1024./2.)]
    print("Master Frame Listo")
    # defino infinidad de parametros  !!MEJORAR ESTO!!
    largo = 100.  # largo en dias de la serie
    d = 2456559   # JD inicial de la serie
    phi_0 = 0.4   # factor que indica luego de que porcentaje
    # de los dias totales de la serie el transitorio tiene el pico
    t_decay = largo*0.05   # tiempo de decaimiento del transitorio
    x = round(1024./2.+45)  # posicion x del transitorio (a explorar)
    y = round(1024./2.)  # posicion y del transitorio (a explorar)
    zero = 23.5  # 12+2.5*np.log10()  #magnitud zero point
    mag_p = 16  # magnitud del pico del transitorio
    for i in range(1, Ntot+1):
        t_exp = 60  #a + (b - a) * (np.random.random_integers(n_p) - 1) / (n_p - 1.)
        # defino el JD random entre c y d,
        # JD=largo * np.random.random_sample() + d
        JD = (largo/Ntot)*i + d
        # encapsulo las imagenes en fits
        MF = inyeccion(Master_F, JD, largo, d, phi_0, t_decay, x, y, zero, mag_p, air)
        A = image(MF, N, t_exp, FWHM, 10)
        capsule_corp(A, JD, t_exp, i, zero)



from astropy.io import fits
from astropy.time import Time
import os
def capsule_corp(gal, t, t_exp, i,zero):
    """
    funcion que encapsula las imagenes generadas en fits
    gal        :   Imagen (matriz) a encapsular
    t          :   Tiempo en dias julianos de esta imagen
    t_exp      :   Tiempo de exposicion de la imagen
    i          :   Numero de imagen
    zero       :   Punto cero de la fotometria
    """
    p = "/media/F038D6A538D669DC/Users/Bruno/Documents/tesis/curvas_sinteticas/Fits_simulados"
    path = os.path.abspath(p)
    s = np.shape(gal)
    for l in range(0, s[0]):
        for j in range(0, s[1]):
            gal[l, j]=round(gal[l, j])

    file1 = fits.PrimaryHDU(gal)
    hdulist = fits.HDUList([file1])
    hdr = hdulist[0].header
    time = Time(t, format='jd', scale='utc')
    dia = time.iso[0:10]
    hora = time.iso[11:24]
    jd = time.jd
    hdr.set('TIME-OBS', hora)
    hdr.set('DATE-OBS', dia)
    hdr.set('EXPTIME', t_exp)
    hdr.set('JD', jd)
    hdr.set('ZERO_P', zero)
    path_fits = os.path.join(path, ('image00'+str(i)+'.fits'))
    hdulist.writeto(path_fits)

