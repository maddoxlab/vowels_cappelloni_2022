form Arguments
    sentence inputSound /Users/vmateo/Dropbox/vowels_edited/ross_neutral_low.wav
    sentence outputSource /Users/vmateo/Documents/Rochester/Semester 8/ross/SOURCE.wav
    sentence outputHP /Users/vmateo/Documents/Rochester/Semester 8/ross/HP.wav
    real hpCutoff 4000
    real skirt 500
    real lpcFreq 10000
    real lpcOrder 12
endform

Read from file... 'inputSound$'
Rename... ORIGINAL
samplerate = Get sampling frequency
numchannels = Get number of channels
if numchannels = 2
    Convert to mono
endif
Filter (pass Hann band)... 0 hpCutoff skirt

#lpcFreq = maxformant*2
#lpcOrder = 12

# first, anti-alias filter
#lpc_antiAlias_LPF = lpcFreq/2
#antiAlias_filterSkirt = 100

# resample to prepare for LPC
#select Sound '.sound$'
Resample... lpcFreq 50
Rename... LPresample
target_resid_intensity = Get intensity (dB)

# create LPC object
To LPC (burg)... lpcOrder 0.025 0.005 50
Rename... FILTER
# yields LPC '.sound$'_'lpcFreq:0'

# inverse filter the sound by the LPC to get the residual glottal source
#select Sound '.sound$'_'lpcFreq:0'
#plus LPC '.sound$'_'lpcFreq:0'
select Sound LPresample
plus LPC FILTER
Filter (inverse)
#Rename... '.sound$'_'lpcFreq'_reFilt

# re-sample back up to the original sampling frequency
# so that it can be combined with other sounds with the original sampling frequency
# (The down-sampled object is never played as a wav file)
Resample... samplerate 50
Scale intensity... target_resid_intensity
Save as WAV file... 'outputSource$'

select Sound ORIGINAL
Filter (stop Hann band)... 0 hpCutoff skirt
Save as WAV file... 'outputHP$'

# cleanup
	#select Sound '.sound$'_'lpcFreq:0'
	#plus Sound '.sound$'_'lpcFreq'_reFilt
	#plus LPC '.sound$'_'lpcFreq:0'
	#Remove
