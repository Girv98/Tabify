FS = 44100                          # Sampling Frequency
NFFT =  2048                        # length of the FFT window
OVERLAP = 0.75                      # Hop overlap percentage
HOP_LENGTH = int(NFFT*(1-OVERLAP))  # Number of samples between successive frames
N_BINS = 84                         # Number of frequency bins
MAG_EXP = 2                         # Magnitude Exponent
PRE_POST_MAX = 6                    # Pre- and post- samples for peak picking
CQT_THRESH = -61                    # Threshold for CQT dB levels, all values below threshold are set to -120 dB


# NFFT = ceil(FS/Fmin)
# ergo, with a FS of 44100
# and NFFT of 2048
# gives a minimum freq res of ~20-22Hz

# FS of 44100 and NFFT of 2048
# gives a minimum freq res of ~31Hz
