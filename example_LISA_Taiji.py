# %%
import numpy as np

import bilby
from bilby.gw import WaveformGenerator
from bilby.gw.detector import get_space_interferometer
from bilby.core.prior import Uniform, Sine
from pycbc.waveform import get_fd_waveform


def PV_waveform(farray, mass_1, mass_2,
                phase, iota, theta, phi, psi, luminosity_distance, geocent_time,
                spin1x, spin1y, spin1z, spin2x, spin2y, spin2z, A, **kwargs):
    approximant = kwargs.get('waveform_approximant', 'IMRPhenomPv2')
    mode_array = kwargs.get('mode_array', [[2, 2]])
    minimum_frequency = kwargs.get('minimum_frequency', farray[0])
    delta_f = farray[1] - farray[0]

    hp, hc = get_fd_waveform(
        approximant=approximant,
        mass1=mass_1, mass2=mass_2,
        distance=luminosity_distance,
        inclination=iota, coa_phase=phase,
        spin1x=spin1x, spin1y=spin1y, spin1z=spin1z,
        spin2x=spin2x, spin2y=spin2y, spin2z=spin2z,
        delta_f=delta_f, f_lower=minimum_frequency, f_final=farray[-1],
        mode_array=mode_array)

    dphi1 = A * (np.pi * farray) ** 2
    waveform_polarizations = {}
    waveform_polarizations['plus'] = (hp + hc * dphi1).numpy()
    waveform_polarizations['cross'] = (hc - hp * dphi1).numpy()
    return waveform_polarizations


def PVam_waveform(farray, mass_1, mass_2,
                  phase, iota, theta, phi, psi, luminosity_distance, geocent_time,
                  spin1x, spin1y, spin1z, spin2x, spin2y, spin2z, B, **kwargs):
    approximant = kwargs.get('waveform_approximant', 'IMRPhenomPv2')
    mode_array = kwargs.get('mode_array', [[2, 2]])
    minimum_frequency = kwargs.get('minimum_frequency', farray[0])
    delta_f = farray[1] - farray[0]

    hp, hc = get_fd_waveform(
        approximant=approximant,
        mass1=mass_1, mass2=mass_2,
        distance=luminosity_distance,
        inclination=iota, coa_phase=phase,
        spin1x=spin1x, spin1y=spin1y, spin1z=spin1z,
        spin2x=spin2x, spin2y=spin2y, spin2z=spin2z,
        delta_f=delta_f, f_lower=minimum_frequency, f_final=farray[-1],
        mode_array=mode_array)

    dh = B * (np.pi * farray)
    waveform_polarizations = {}
    waveform_polarizations['plus'] = (hp - hc * dh * 1j).numpy()
    waveform_polarizations['cross'] = (hc + hp * dh * 1j).numpy()
    return waveform_polarizations


# %%
injection_parameters = dict(mass_1=5e6, mass_2=3e6, phase=1., iota=1.3, theta=1, phi=3, psi=np.pi / 3,
                            luminosity_distance=20e3, geocent_time=1126259642.4,
                            spin1x=0., spin1y=0., spin1z=0., spin2x=0., spin2y=0., spin2z=0., A=0)

duration = 2**18
sampling_frequency = 1 / 16

np.random.seed(0)
outdir = 'LISA_Taiji_PV'
label = 'PV'
bilby.core.utils.setup_logger(outdir=outdir, label=label)

minimum_frequency = 1e-4
maximum_frequency = 1e-2
waveform_arguments = dict(waveform_approximant='IMRPhenomXHM',
                          minimum_frequency=minimum_frequency)


def PV_generator_from_mode(mode):
    wf_args = waveform_arguments.copy()
    wf_args.update({'mode_array': [mode]})
    return WaveformGenerator(duration=duration, sampling_frequency=sampling_frequency,
                             frequency_domain_source_model=PV_waveform,
                             parameter_conversion=bilby.gw.conversion.convert_to_lal_binary_black_hole_parameters,
                             waveform_arguments=wf_args,
                             init_log=False)


def PVam_generator_from_mode(mode):
    wf_args = waveform_arguments.copy()
    wf_args.update({'mode_array': [mode]})
    return WaveformGenerator(duration=duration, sampling_frequency=sampling_frequency,
                             frequency_domain_source_model=PVam_waveform,
                             parameter_conversion=bilby.gw.conversion.convert_to_lal_binary_black_hole_parameters,
                             waveform_arguments=wf_args,
                             init_log=False)


# %%
mode_array = [[2, 2], [2, 1], [3, 3], [4, 4], [5, 5]]
frequency_array = PV_generator_from_mode([2, 2]).frequency_array
lisa = get_space_interferometer('LISA', frequency_array, PV_generator_from_mode, mode_array,
                                minimum_frequency=minimum_frequency, maximum_frequency=maximum_frequency)
taiji = get_space_interferometer('Taiji', frequency_array, PV_generator_from_mode, mode_array,
                                 minimum_frequency=minimum_frequency, maximum_frequency=maximum_frequency)
# tianqin = get_space_interferometer('Tianqin', frequency_array, PV_generator_from_mode, mode_array,
#                                   minimum_frequency=minimum_frequency, maximum_frequency=maximum_frequency)

ifos = lisa
ifos.extend(taiji)
# ifos.extend(tianqin)

ifos.set_strain_data_from_power_spectral_densities(
    sampling_frequency=sampling_frequency, duration=duration,
    start_time=injection_parameters['geocent_time'] - duration + 2096)
ifos.inject_signal(waveform_generator=PV_generator_from_mode([2, 2]),
                   parameters=injection_parameters)
# ifos.plot_data(outdir=outdir)
# %%
priors = {}
for key, value in injection_parameters.items():
    priors[key] = value

priors['mass_1'] = Uniform(minimum=1e5, maximum=1e7, name='mass_1', unit=r'$M_\odot$')
priors['mass_2'] = Uniform(minimum=1e5, maximum=1e7, name='mass_2', unit=r'$M_\odot$')

priors['phase'] = Uniform(name='phase', minimum=0, maximum=2 * np.pi, boundary='periodic')
priors['iota'] = Sine(name='iota')
priors['theta'] = Uniform(
    name='theta', minimum=0, maximum=np.pi, boundary='periodic', latex_label=r'$\theta_e$')
priors['phi'] = Uniform(name='phi', minimum=0, maximum=2 * np.pi,
                        boundary='periodic', latex_label=r'$\phi_e$')
priors['psi'] = Uniform(name='psi', minimum=0, maximum=np.pi,
                        boundary='periodic', latex_label=r'$\psi$')

priors['luminosity_distance'] = Uniform(minimum=1e3, maximum=1e5, name='luminosity_distance', unit=r'$\mathrm{Mpc}$')

priors['geocent_time'] = Uniform(
    minimum=injection_parameters['geocent_time'] - 10,
    maximum=injection_parameters['geocent_time'] + 10,
    name='geocent_time', unit=r'$\mathrm{s}$')
'''
for key in ['spin1x', 'spin1y', 'spin1z', 'spin2x', 'spin2y', 'spin2z']:
    priors[key] = Uniform(minimum = -0.5, maximum = 0.5, name=key)    
'''
priors['A'] = Uniform(minimum=-1e3, maximum=1e3, name='A', unit=r'$\mathrm{Hz}^{-2}$')

# %%
# waveform_generator here is not applied in calculating likelihood, because we only use parameters injected to calculate response.
likelihood = bilby.gw.likelihood.GravitationalWaveTransient(
    interferometers=ifos, waveform_generator=PV_generator_from_mode([2, 2]), priors=priors, reference_frame='ecliptic')

# %%
sampler = 'pymultinest'

result = bilby.run_sampler(
    likelihood=likelihood, priors=priors, sampler=sampler, npoints=1000,
    injection_parameters=injection_parameters, outdir=outdir, label=label)

result.convert_result_mass()
result.plot_corner(quantiles=[0.05, 0.95])