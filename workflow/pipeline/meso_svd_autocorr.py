"""This module was auto-generated by datajoint from an existing schema"""

import datajoint as dj
import numpy as np
from bisect import bisect
from math import *
#import statsmodels.api as sm

schema = dj.Schema('lee_meso_analysis')

exp2 = dj.VirtualModule('exp2', 'arseny_s1alm_experiment2')
img = dj.VirtualModule('img', 'arseny_learning_imaging')
meso = dj.VirtualModule('meso', 'lee_meso_analysis')


@schema
class SVDTemporalComponentsAutocorr3(dj.Computed):
    definition = """
    -> exp2.SessionEpoch
    component_id         : int                          
    threshold            : double                       # threshold for defining the autocorrelation timescale
    time_bin             : double                       # time window used for binning the data. 0 means no binning
    ---
    temporal_component_autocorr: blob           # the auto correlation of the temporal component of the SVD
    temporal_component_autocorr_tau: blob       # the time constant of the auto correlation, a vector of taus for each component """

    @property
    def key_source(self):
        return (exp2.SessionEpoch & meso.SVDTemporalComponentsPython & img.Mesoscope)

    def make(self, key):

        time_bin_vector = [0, 1.5]
        threshold_vector = [1, 2]
        lags = 50

        rel_FOVEpoch = img.FOVEpoch & key
        rel_FOV = img.FOV & key
        if 'imaging_frame_rate' in rel_FOVEpoch.heading.secondary_attributes:
            imaging_frame_rate = rel_FOVEpoch.fetch1('imaging_frame_rate')
        else:
            imaging_frame_rate = rel_FOV.fetch1('imaging_frame_rate')
     
        for time_bin in time_bin_vector:
            for threshold in threshold_vector:

                key['time_bin'] = time_bin
                key['threshold'] = threshold
                rel_comp = meso.SVDTemporalComponents & key
                temporal_components = np.asarray(rel_comp.fetch('temporal_component', order_by='component_id'))
                num_comp = temporal_components.shape[0]

                tau = np.empty((num_comp,1))
                acorr_all = np.empty((num_comp,lags))
                for i in range(num_comp):

                    data = temporal_components[i]
                    mean = np.mean(data)
                    var = np.var(data)
                    ndata = data - mean
                    acorr = np.correlate(ndata, ndata, 'full')[len(ndata)-1:] 
                    acorr = acorr[range(lags)] / var / len(ndata)
                  #  acorr = sm.tsa.acf(data, nlags = lags-1)
                    time_bin_scaling = time_bin
                    if time_bin == 0:
                        time_bin_scaling = 1
                    ts = np.argmax(acorr < np.exp(-threshold)) / imaging_frame_rate * time_bin_scaling
                    if ts == 0:
                        ts = lags
                    tau[i] = ts
                    acorr_all[i] = acorr

                key_meso = {**key, 'time_bin': time_bin, 'threshold': threshold}    
                key_comps = [{**key_meso, 'component_id': ic, 'temporal_component_autocorr_tau': tau[ic], 'temporal_component_autocorr': acorr_all[ic]}
                                for ic in range(num_comp)]
                self.insert(key_comps, allow_direct_insert=True)
