"""
Created on Wed Feb 19 03:22:05 2020

@author: James Girven
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy import signal
import librosa, librosa.display
import re

import fretboard as fb

import os

from variables import (
    NFFT,
    HOP_LENGTH,
    N_BINS,
    MAG_EXP,
    PRE_POST_MAX,
    CQT_THRESH)

def main(path, file, tuning, fmin, n_frets):
    
    filepath = path + file

    x, fs = librosa.load(filepath, sr=None, mono=True)

    print(file)
    print("Shape:", x.shape)
    print("Sample Rate:", fs)
    print("Length = {:f} seconds".format(x.shape[0]/fs))
    print("")

    print(fmin)
    cqt = calc_cqt(x, fs, fmin = librosa.note_to_hz(fmin))

    plt.figure()
    
    
    new_cqt = cqt_thresholded(cqt)
                            #new_cqt
    librosa.display.specshow(cqt, sr=fs, hop_length=HOP_LENGTH, x_axis='time', y_axis='cqt_note', cmap='coolwarm', fmin=librosa.note_to_hz(fmin))    
    
    onsets = calc_onset(new_cqt,fs)
    print(len(onsets[0]), "onsets found at:")
    print(onsets[0])

    print()
    music_info = np.array([
        estimate_pitch_and_notes(cqt, onsets[1], i, sr=fs, fmin = librosa.note_to_hz(fmin))
        for i in range(len(onsets[1])-1)
    ])

    a = np.array([x for x in music_info if x[0] is not None])
    #print(a)
    print("Length :", len(a))

    notes = np.array([librosa.hz_to_midi(x[0]) for x in a])
    print(notes)
    print("Number of notes/chords found:", len(notes))
    print()


    midi_tuning = []
    for i in tuning:
        midi_tuning.append(librosa.note_to_midi(i))

        
    fb.analyse(notes, midi_tuning, n_frets, file)
    
    #print(librosa.hz_to_note(184.99))
    
    plt.vlines(onsets[0], 0, fs/2, color='k', alpha=0.8)
    plt.title("CQT for {:s}".format(file))
    plt.colorbar()

    outpath = 'output/cqt/'
    plt.savefig(outpath + os.path.splitext(file)[0] + '.png')
    plt.show()


# calculate CQT, returns magnitude in deciBells 
def calc_cqt(x,fs,hop_length=HOP_LENGTH, n_bins=N_BINS, mag_exp=MAG_EXP, fmin=librosa.note_to_hz('E2')):
    print(fmin)
    C = librosa.cqt(x, sr=fs, hop_length=hop_length, fmin=fmin, n_bins=n_bins, res_type='fft')
    C_mag = librosa.magphase(C)[0]**mag_exp
    CdB = librosa.core.amplitude_to_db(C_mag ,ref=np.max)
    return CdB

# Thresholds CQT, sets values under threshold to -120dB
def cqt_thresholded(cqt,thres=CQT_THRESH):
    new_cqt=np.copy(cqt)
    new_cqt[new_cqt<thres]= -120
    return new_cqt


# Onset Envelope from Cqt
def calc_onset_env(cqt,fs):
    return librosa.onset.onset_strength(S=cqt, sr=fs, aggregate=np.mean, hop_length=HOP_LENGTH)

# Onset from Onset Envelope                        backtrack = True
def calc_onset(cqt, fs, pre_post_max=PRE_POST_MAX, backtrack=True):
    onset_env = calc_onset_env(cqt, fs)
    onset_frames = librosa.onset.onset_detect(onset_envelope=onset_env,
                                           sr=fs, units='frames', 
                                           hop_length=HOP_LENGTH, 
                                           backtrack=backtrack,
                                           pre_max=pre_post_max,
                                           post_max=pre_post_max)
    onset_boundaries = np.concatenate([[0], onset_frames, [cqt.shape[1]]])
    onset_times = librosa.frames_to_time(onset_boundaries, sr=fs, hop_length=HOP_LENGTH)
    return [onset_times, onset_boundaries, onset_env]

def estimate_pitch(segment, threshold, fmin = librosa.note_to_hz('E2')):
    freqs = librosa.cqt_frequencies(n_bins=N_BINS, fmin=fmin, bins_per_octave=12)
    if segment.max()<threshold:
        return [None]
    else:
        first_max = np.argmax(segment,axis=0)

        new_seg=np.copy(segment)
        new_seg[segment<threshold]= -120
        
        nu_peaks, x2 = np.array(signal.find_peaks(new_seg))

        if nu_peaks.size == 0:
            return [None]

        f_lists = []
        for i in nu_peaks:
            if abs(new_seg[i]) < 50:
                f_lists.append(i)

        if not f_lists:
            f_lists = np.copy(nu_peaks)


        print("possible frequencies",f_lists)
                
        f0_lists = []
        f0_lists.append(f_lists[0])
        for i in range(1,len(f_lists)):
            if (f_lists[i] - f_lists[i-1]) % 12 != 0 and abs(new_seg[f_lists[i]]) <  abs(new_seg[f_lists[0]])/2: 
                f0_lists.append(f_lists[i])
        print("chosen frequencies",f0_lists)
        print()
        
        f_freqs = []
        for i in f0_lists:
            f_freqs.append(freqs[i])
       
    return [np.array(f_freqs)]

def estimate_pitch_and_notes(x, onset_boundaries, i, sr, fmin=librosa.note_to_hz('E2')):
    n0 = onset_boundaries[i]
    n1 = onset_boundaries[i+1]
    f0_info = estimate_pitch(np.mean(x[:,n0:n1],axis=1),threshold=CQT_THRESH, fmin=fmin)
    return f0_info


if __name__ == '__main__':

    print("Welcome")
    print()
    
    path = 'music/'
    file = 'fsharp_minorscale.wav'

    print("Please put .wav file into the music folder")
    file = input("Enter filename (i.e. fsharp_minorscale.wav):")
    
    #file = 'indie.wav'
    #file = 'fsharp_minorscale.wav'
    
    tuning = ['E2','A2','D3','G3','B3','E4']
    n_frets = 21

    
    print("The default setting is standard tuning, 6 strings and 21 frets")
    x = input("Press Enter to continue, enter anything else to change")
    if x != '':
        print("Input tuning in the form: E2 A3 D3 G3 B3 E4")
        print("With lowest string first")
        input_string = input("Please enter -> ")
        tuning = input_string.split()
        n_frets = int(input("Input Number of Frets:"))
        print(tuning)
        print(tuning[0])

    main(path, file, tuning, tuning[0],n_frets)
        


