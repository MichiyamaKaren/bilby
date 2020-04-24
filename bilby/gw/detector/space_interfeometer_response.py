#%%
'''
Calculate response for space detectors LISA, TianQin.
'''

import numpy as np
import matplotlib.pyplot as plt

# %% PV waveform
from pycbc.waveform import get_fd_waveform
from ..waveform_generator import WaveformGenerator
from ..conversion import convert_to_lal_binary_black_hole_parameters

approx = 'IMRPhenomXHM'

def PV_waveform(farray, mass_1, mass_2,
                phase, iota, theta, phi, psi, luminosity_distance, geocent_time,
                spin1x, spin1y, spin1z, spin2x, spin2y, spin2z, A, mode_array, **kwargs):
    flow = 1e-4
    fhigh = farray[-1]
    deltaf = farray[1] - farray[0]

    waveform_polarizations = {}
    hp, hc = \
    get_fd_waveform(approximant=approx,
        mass1=mass_1, mass2=mass_2,
        distance=luminosity_distance,
        inclination=iota, coa_phase=phase,
        spin1x=spin1x, spin1y=spin1y, spin1z=spin1z,
        spin2x=spin2x, spin2y=spin2y, spin2z=spin2z,
        delta_f=deltaf, f_lower=flow, f_final=fhigh,
        mode_array=mode_array)

    dphi1 = A * (np.pi * farray)** 2
    waveform_polarizations['plus'] = (hp + hc * dphi1).numpy()
    waveform_polarizations['cross'] = (hc - hp * dphi1).numpy()
    return waveform_polarizations


def PV_waveform_from_mode(mode_array):
    def waveform(farray, mass_1, mass_2, phase, iota, theta, phi, psi, luminosity_distance, geocent_time,
                 spin1x, spin1y, spin1z, spin2x, spin2y, spin2z, A, **kwargs):
        return PV_waveform(farray, mass_1, mass_2, phase, iota, theta, phi, psi, luminosity_distance, geocent_time,
                           spin1x, spin1y, spin1z, spin2x, spin2y, spin2z, A, mode_array, **kwargs)
    
    return waveform

duration = 2**18
sampling_frequency = 1/16.

def PV_generator_from_mode(mode_array):
    return WaveformGenerator(
        duration=duration, sampling_frequency=sampling_frequency,
        frequency_domain_source_model=PV_waveform_from_mode(mode_array),
        parameter_conversion=convert_to_lal_binary_black_hole_parameters)

# %%  Antenna pattern function in detector frame
# References:
# Cutler, https://arxiv.org/abs/gr-qc/9703068v1
# Zhao, https://arxiv.org/abs/1009.0206v4
# Liang, arXiv:1901.09624v3
def fplus(gamma, theta, phi, psi):
    '''
    gamma: angle between interferometer arms 
    theta, phi: source direction in detector frame
    psi: polarization angle
    (in radians)
    '''
    A = np.sin(gamma)
    B = 0.5*(1+np.cos(theta)**2)*np.cos(2*phi)*np.cos(2*psi)
    C = -np.cos(theta)*np.sin(2*phi)*np.sin(2*psi)
    return A*(B+C)

def fcross(gamma, theta, phi, psi):
    '''
    gamma: angle between interferometer arms
    theta, phi: source direction in detector frame
    psi: polarization angle
    (in radians)
    '''
    A = np.sin(gamma)
    B = 0.5*(1+np.cos(theta)**2)*np.cos(2*phi)*np.sin(2*psi)
    C = np.cos(theta)*np.sin(2*phi)*np.cos(2*psi)
    return A*(B+C)

# %% Time t corresponding frequency f, using SPA.

def tf_spa(f, tc, m1, m2):
    '''
    h(t) = F_+(t)*h_+(t) + F_x(t)*h_x(t)
    Fourier Transfrom, we get
    h(f) = F_+(f)*h_+(f) + F_x(f)*h_x(f)
    However, antenna response in f domain F(f) is hard to obtain, so we use stationary phase approximation(SPA), changing F(f) into F(t(f)) which is a function in time domain.

    This is the function calculating the t(f).

    unit: f-Hz, tc-s, m1m2-solar mass

    See (A12) in Niu, arXiv:1910.10592
    '''
    m1 = m1*2e30
    m2 = m2*2e30
    M = m1+m2
    eta = m1*m2/M**2
    M_c = eta**0.6*M
    G = 6.67e-11
    c = 299792458
    pi = np.pi
    v = (G*M*2*pi*f/c**3)**(1/3)
    v = v.astype('float64')
    t =  tc - c**(5)*5/256*(G*M_c)**(-5/3)*(2*pi*f)**(-8/3)*(1*v**(0)
        +4/3*(743/336+(11/4)*eta)*v**(2)
        +(-32*pi/5)*v**(3)
        +(3058673/508032+5429/504*eta+617/72*eta**2)*v**(4)
        +(-7729/252+13/3*eta)*pi*v**(5) 
        +(-10052469856691/23471078400+128/3*pi**2+6848/105*0.577+3424/105*np.log(16*v**2)+(3147553127/3048192-451/12*pi**2)*eta-15211/1728*eta**2+25565/1296*eta**3)*v**(6)
        +(-15419335/127008-75703/756*eta+14809/378*eta**2)*pi*v**(7))

    t = t.astype('float64')

    return t


def tf_spa_from_mode(f, tc, m1, m2, mode):
    '''
    See (4.8) in arXiv:2001.10914v1
    '''
    m = mode[1]
    return tf_spa(f / m, tc, m1, m2)


def get_mode_from_name(name):
    try:
        mode = [int(i) for i in name.split('_')[-1]]
        if len(mode) != 2:
            raise Exception
        return mode
    except:
        return [2, 2]

# %%
# Polarization tensor in ecliptic frame

def polarization_tensor_ecliptic(theta,phi,psi,polarization):
    '''
    Return the polarization tensor e_ij of GW in ecliptic frame
    polarizarion should be 'plus' or 'cross'

    Reference: 
    Liang, arXiv:1901.09624v3
    '''
    '''
    m = np.array([\
    np.cos(theta)*np.cos(phi)*np.cos(psi)+np.sin(phi)*np.sin(psi),\
    np.cos(theta)*np.sin(phi)*np.cos(psi)-np.cos(phi)*np.sin(psi),\
    -np.sin(theta)*np.cos(psi)])

    n = np.array([\
    -np.cos(theta)*np.cos(phi)*np.sin(psi)+np.sin(phi)*np.cos(psi),\
    -np.cos(theta)*np.sin(phi)*np.sin(psi)-np.cos(phi)*np.cos(psi),\
    np.sin(theta)*np.sin(psi)])
    '''
    p = np.array([np.cos(theta) * np.cos(phi),
                  np.cos(theta) * np.sin(phi),
                  - np.sin(theta)])
    q = np.array([np.sin(phi), -np.cos(phi), 0])
    
    ep = np.einsum('i,j',p,p) - np.einsum('i,j',q,q)
    ec = np.einsum('i,j',p,q) + np.einsum('i,j',q,p)

    if polarization == 'plus':
        return ep * np.cos(2 * psi) - ec * np.sin(2 * psi)
    elif polarization == 'cross':
        return ep * np.sin(2 * psi) + ec * np.cos(2 * psi)
    else:
        raise Exception("Polarization should be 'plus' or 'cross'")

# %%
# LISA orbit, arm direction and detector tensor

def arm_direction_lisa(i,t):
    '''
    Calculate the unit vector along the i-th arm of LISA in ecliptic frame. 

    Cutler    Liang
     l_1        u
     l_2        v

    i: 1,2,3
    t: timeseries

    Reference: 
    Cutler, arXiv:gr-qc/9703068v1
    Liang, arXiv:1901.09624v3
    '''
    T = 31536000.0  # seconds in a year
    alpha_i = 2*np.pi*t/T - np.pi/12 - (i-1)*np.pi/3
    phi = 2*np.pi*t/T

    ex = np.cos(phi)*np.sin(alpha_i)/2 - np.sin(phi)*np.cos(alpha_i)
    ey = np.sin(phi)*np.sin(alpha_i)/2 + np.cos(phi)*np.cos(alpha_i)
    ez = np.sqrt(3)*np.sin(alpha_i)/2
    tmp = np.array([ex,ey,ez])
    return np.einsum('ji',tmp)  # transpose


def orbit_lisacenter(t):
    R = 1.4959787e11  # 1AU, unit:m
    L = 2.5e9         # arm length of LISA
    T = 31536000.0    # seconds in a year
    phi = 2 * np.pi * t / T + 20 * np.pi / 180

    # center of mass
    r0 = np.array([R*np.cos(phi), R*np.sin(phi), np.zeros(len(t))])
    r0 = np.einsum('ji',r0)
    return r0


def orbit_lisa(n,t):
    '''
    Calculate LISA's orbit r = ( x(t),y(t),z(t) ) in ecliptic frame
    t: time(s)
    n: =1,2,3, representing 3 detectors

    Reference: Cutler, 1998
    '''
    R = 1.4959787e11  # 1AU, unit:m
    L = 2.5e9         # arm length of LISA
    T = 31536000.0    # seconds in a year
    phi = 2 * np.pi * t / T

    # center of mass
    r0 = np.array([R*np.cos(phi), R*np.sin(phi), np.zeros(len(t))])
    r0 = np.einsum('ji',r0)
    if n==1:
        L1 = L*arm_direction_lisa(1,t)
        L2 = L*arm_direction_lisa(2,t)
        return r0 - (L1+L2)/3
    elif n==2:
        L1 = L*arm_direction_lisa(1,t)
        L3 = L*arm_direction_lisa(3,t)
        return r0 - (L3-L1)/3
    elif n==3:
        L2 = L*arm_direction_lisa(2,t)
        L3 = L*arm_direction_lisa(3,t)
        return r0 + (L2+L3)/3
    else:
        raise Exception('Wrong detector index')


def detector_tensor_lisa1(t):
    '''
    Return detector tensor of LISA in ecliptic frame.
    Definition of detector tensor is D_ij = 1/2*(uiuj-vivj)
    LISA has two strain output, this function gives the first one.

    Reference: 
    Liang, arXiv:1901.09624v3
    '''
    u = arm_direction_lisa(1,t)
    v = arm_direction_lisa(2,t)
    return 0.5*(np.einsum('ai,aj->aij',u,u)-np.einsum('ai,aj->aij',v,v))


def detector_tensor_lisa2(t):
    '''
    Return detector tensor of LISA in ecliptic frame.
    Definition of detector tensor is D_ij = 1/2*(uiuj-vivj)
    LISA has two strain output, this function gives the second one.
    
    Reference: 
    Liang, arXiv:1901.09624v3
    '''
    u = (-1.0)*arm_direction_lisa(1,t)
    v = arm_direction_lisa(3,t)
    return 0.5*(np.einsum('ai,aj->aij',u,u)-np.einsum('ai,aj->aij',v,v))


def detector_tensor_lisaa(t):
    '''
    Return detector tensor of LISA in ecliptic frame.
    Definition of detector tensor is D_ij = 1/2*(uiuj-vivj)
    LISA has two strain output, this function gives the lisa a.

    Reference: 
    
    '''
    n1 = arm_direction_lisa(1,t)
    n2 = arm_direction_lisa(2,t)
    n3 = arm_direction_lisa(3,t)
    return 1/6*(np.einsum('ai,aj->aij',n1,n1)-2*np.einsum('ai,aj->aij',n2,n2)+np.einsum('ai,aj->aij',n3,n3))


def detector_tensor_lisae(t):
    '''
    Return detector tensor of LISA in ecliptic frame.
    Definition of detector tensor is D_ij = 1/2*(uiuj-vivj)
    LISA has two strain output, this function gives the lisa e.

    Reference: 
    
    '''
    n1 = arm_direction_lisa(1,t)
    #n2 = arm_direction_lisa(2,t)
    n3 = arm_direction_lisa(3,t)
    return np.sqrt(3) / 6 * (np.einsum('ai,aj->aij', n1, n1) - np.einsum('ai,aj->aij', n3, n3))


def detector_tensor_lisa(name, t):
    '''
    if name == 'lisa1':
        return detector_tensor_lisa1(t)
    elif name == 'lisa2':
        return detector_tensor_lisa2(t)
    elif name == 'lisaa':
        return detector_tensor_lisaa(t)
    elif name == 'lisae':
        return detector_tensor_lisae(t)
    '''
    if name.startswith('lisa_a'):
        return detector_tensor_lisaa(t)
    elif name.startswith('lisa_e'):
        return detector_tensor_lisae(t)
    else:
        raise Exception("Name 'lisa_a_xxx' or 'lisa_e_xxx' supposed.")


def lisa_time_difference_to_sun(theta, phi, t, n):
    '''
    reference: arXiv:1803.03368v1
    '''
    c = 299792458
    Omega = - np.array([np.sin(theta) * np.cos(phi),
                        np.sin(theta) * np.sin(phi),
                        np.cos(theta)])
    rnc = orbit_lisa(n, t) / c  # rn / c
    return np.einsum('j,ij->i', Omega, rnc)


def lisa_time_difference_to_sun_center(theta, phi, t):
    '''
    reference: arXiv:1803.03368v1
    '''
    c = 299792458
    Omega = - np.array([np.sin(theta) * np.cos(phi),
                        np.sin(theta) * np.sin(phi),
                        np.cos(theta)])
    r0 = orbit_lisacenter(t) / c  # r0 / c
    return np.einsum('j,ij->i', Omega, r0)


def get_lisa_fresponse(name, waveform, theta, phi, psi, t):
    '''
    Get LISA's response in freq domain

    t: time(s), should be converted from freq series by tf_spa
    hp,hc: waveform in source frame (f domain)
    theta,phi,psi: source location in ecliptic frame

    Note that this function can be also used to calculate time domain response, as long as hp&hc are given in time domain with cooresponding timeseries t.
    '''
    D = detector_tensor_lisa(name, t)
    signal = {}
    for mode in ['plus', 'cross']:
        polarization_tensor = polarization_tensor_ecliptic(theta, phi, psi, mode)
        F = np.einsum('aij,ij->a', D, polarization_tensor)
        signal[mode] = waveform[mode] * F
    return sum(signal.values())

# %%
# TianQin orbit, arm direction and detector tensor

def tianqin_spacecraft(n, t):
    '''
    Calculate coordinate of TianQin spacecraft r = ( x(t),y(t),z(t) ) in ecliptic frame.
    Assuming TianQin is moving in a circular orbit around Earth.
    
    n: 1,2,3
    t: time array

    Reference:
    arXiv:1803.03368
    '''
    R = 1.4959787e11  # 1AU
    e = 0.0167        # eccentricity of the geocenter orbit around the Sun
    fm = 3.14e-8      # 1 / (1 sidereal year)
    R1 = 1e8
    fsc = 1 / 315360  # 1 / (3.65 days), frequency of the detector rotation around the Earth
    theta_s = -4.7 * np.pi / 180
    phi_s = 120.5 * np.pi / 180

    alpha = 2 * np.pi * fm * t
    alpha_n = 2 * np.pi * fsc * t + 2 * np.pi / 3 * (n - 1)

    x = R1 * (np.cos(phi_s) * np.sin(theta_s) * np.sin(alpha_n) + np.cos(alpha_n) * np.sin(phi_s)) + R * np.cos(
        alpha) + 0.5 * R * e * (2 * np.cos(2 * alpha) - 3) - 1.5 * R * e ** 2 * np.cos(alpha) * (np.sin(alpha) ** 2)
    y = R1 * (np.sin(phi_s) * np.sin(theta_s) * np.sin(alpha_n) - np.cos(alpha_n) * np.cos(phi_s)) + R * np.sin(
        alpha) + 0.5 * R * e * np.sin(2 * alpha) + 0.25 * R * e ** 2 * (3 * np.cos(2 * alpha) - 1) * np.sin(alpha)
    z = -R1 * np.sin(alpha_n) * np.cos(theta_s)
    
    return np.array([x, y, z]).transpose()


def arm_direction_tianqin(n, t):
    '''
    Calculate the unit vector along the i-th arm of TianQin in ecliptic frame.
    Assuming TianQin is moving in a circular orbit around Earth. 

    n: 1,2,3
    t: time array

    Reference: 
    arXiv:1803.03368
    '''

    fsc = 1 / 315360  # 1 / (3.65 days), frequency of the detector rotation around the Earth
    theta_s = -4.7 * np.pi / 180
    phi_s = 120.5 * np.pi / 180
    
    alpha_n = 2 * np.pi * fsc * t + 2 * np.pi / 3 * n - np.pi / 3

    x = np.cos(phi_s) * np.sin(theta_s) * np.cos(alpha_n) - np.sin(alpha_n) * np.sin(phi_s)
    y = np.sin(phi_s) * np.sin(theta_s) * np.cos(alpha_n) + np.sin(alpha_n) * np.cos(phi_s)
    z = -np.cos(alpha_n) * np.cos(theta_s)
    return np.array([x, y, z]).transpose()


def tianqin_center_orbit(t):
    '''
    Orbit of TianQin's center, i.e., the Earth.
    '''

    R = 1.4959787e11  # 1AU
    e = 0.0167        # eccentricity of the geocenter orbit around the Sun
    fm = 3.14e-8      # 1 / (1 sidereal year)
    
    alpha = 2 * np.pi * fm * t

    # center of mass
    x = R * np.cos(alpha) + 0.5 * R * e * (np.cos(2 * alpha) - 3) - 1.5 * R * e ** 2 * np.cos(alpha) * (np.sin(alpha)** 2)
    y = R * np.sin(alpha) + 0.5 * R * e * np.sin(2 * alpha) + 0.25 * R * e ** 2 * (3 * np.cos(2 * alpha) - 1) * np.sin(alpha)
    z = np.zeros(t.shape)
    return np.array([x, y, z]).transpose()


def tianqin_time_difference_to_sun_center(theta, phi, t):
    '''
    reference: arXiv:1803.03368v1
    '''
    c = 299792458
    Omega = - np.array([np.sin(theta) * np.cos(phi),
                        np.sin(theta) * np.sin(phi),
                        np.cos(theta)])
    r0 = tianqin_center_orbit(t) / c  # r0 / c
    return np.einsum('j,ij->i', Omega, r0)


def detector_tensor_tianqin(name, t):
    '''
    Return detector tensor of TianQin in ecliptic frame.
    Definition of detector tensor is D_ij = 1/2*(uiuj-vivj)

    Reference: 
    arXiv:2003.00357
    '''
    n1 = arm_direction_tianqin(1, t)
    n2 = arm_direction_tianqin(2, t)
    n3 = arm_direction_tianqin(3, t)

    if name.startswith('tianqin_a'):
        return 1 / 6 * (np.einsum('ai,aj->aij', n1, n1) - 2 * np.einsum('ai,aj->aij', n2, n2) + np.einsum('ai,aj->aij', n3, n3))
    elif name.startswith('tianqin_e'):
        return np.sqrt(3) / 6 * (np.einsum('ai,aj->aij', n1, n1) - np.einsum('ai,aj->aij', n3, n3))
    else:
        raise Exception("Name 'tianqin_a_xxx', or 'tianqin_e_xxx' supposed.")


def get_tianqin_fresponse(name, waveform, theta, phi, psi, t):
    '''
    Get TianQin's response in frequency domain

    Input:
        name: str, detector name('tianqin_a' or 'tianqin_e' supposed)
        waveform: dict, polarizations of waveform
        theta, phi, psi: source location in ecliptic frame
        t: time array corresponding of frequency array
    '''
    
    D = detector_tensor_tianqin(name, t)
    signal = {}
    for mode in ['plus', 'cross']:
        polarization_tensor = polarization_tensor_ecliptic(theta, phi, psi, mode)
        F = np.einsum('aij,ij->a', D, polarization_tensor)
        signal[mode] = waveform[mode] * F
    return sum(signal.values())

# %% Taiji response
def arm_direction_taiji(i,t):
    '''
    Calculate the unit vector along the i-th arm of taiji in ecliptic frame. 
    '''
    T = 31536000.0  # seconds in a year
    alpha_i = 2*np.pi*t/T - np.pi/12 - (i-1)*np.pi/3
    phi = 2*np.pi*t/T

    ex = np.cos(phi)*np.sin(alpha_i)/2 - np.sin(phi)*np.cos(alpha_i)
    ey = np.sin(phi)*np.sin(alpha_i)/2 + np.cos(phi)*np.cos(alpha_i)
    ez = np.sqrt(3)*np.sin(alpha_i)/2
    tmp = np.array([ex,ey,ez])
    return np.einsum('ji',tmp)  # transpose


def orbit_taijicenter(t):
    R = 1.4959787e11  # 1AU, unit:m
    L = 2.5e9         # arm length of taiji
    T = 31536000.0    # seconds in a year
    phi = 2 * np.pi * t / T - 20 * np.pi / 180

    # center of mass
    r0 = np.array([R*np.cos(phi), R*np.sin(phi), np.zeros(len(t))])
    r0 = np.einsum('ji',r0)
    return r0


def detector_tensor_taijia(t):
    '''
    Return detector tensor of taiji_a in ecliptic frame.
    '''
    n1 = arm_direction_taiji(1, t)
    n2 = arm_direction_taiji(2, t)
    n3 = arm_direction_taiji(3, t)
    return 1/6*(np.einsum('ai,aj->aij',n1,n1)-2*np.einsum('ai,aj->aij',n2,n2)+np.einsum('ai,aj->aij',n3,n3))


def detector_tensor_taijie(t):
    '''
    Return detector tensor of taiji_e in ecliptic frame.
    '''
    n1 = arm_direction_taiji(1, t)
    n3 = arm_direction_taiji(3, t)
    return np.sqrt(3) / 6 * (np.einsum('ai,aj->aij', n1, n1) - np.einsum('ai,aj->aij', n3, n3))


def detector_tensor_taiji(name, t):
    if name.startswith('taiji_a'):
        return detector_tensor_taijia(t)
    elif name.startswith('taiji_e'):
        return detector_tensor_taijie(t)
    else:
        raise Exception("Name 'taiji_a_xxx' or 'taiji_e_xxx' supposed.")


def taiji_time_difference_to_sun_center(theta, phi, t):
    '''
    reference: arXiv:1803.03368v1
    '''
    c = 299792458
    Omega = - np.array([np.sin(theta) * np.cos(phi),
                        np.sin(theta) * np.sin(phi),
                        np.cos(theta)])
    r0 = orbit_taijicenter(t) / c  # r0 / c
    return np.einsum('j,ij->i', Omega, r0)


def get_taiji_fresponse(name, waveform, theta, phi, psi, t):
    '''
    Get TaiJi's response in frequency domain

    Input:
        name: str, detector name('taiji_a_xxx' or 'taiji_e_xxx' supposed)
        waveform: dict, polarizations of waveform
        theta, phi, psi: source location in ecliptic frame
        t: time array corresponding of frequency array
    '''
    
    D = detector_tensor_taiji(name, t)
    signal = {}
    for mode in ['plus', 'cross']:
        polarization_tensor = polarization_tensor_ecliptic(theta, phi, psi, mode)
        F = np.einsum('aij,ij->a', D, polarization_tensor)
        signal[mode] = waveform[mode] * F
    return sum(signal.values())