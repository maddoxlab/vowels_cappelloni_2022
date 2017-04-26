form Arguments
    sentence GridFile GRID.formantGrid
    sentence SourceSound SOURCE.wav
    sentence HpSound HP.wav
    positive HpCutoff 4000
    positive Skirt 500
    real Start 
    real End
    sentence OutputSound
endform

Read from file... 'gridFile$'
Rename... GRID
Read from file... 'sourceSound$'
Rename... SOURCE
Read from file... 'hpSound$'
Rename... HP

#original_LP_intensity = 78.85376167020497

#sourceFilterResynth
select Sound SOURCE
plus FormantGrid GRID
Filter
Rename... Output_SF

#makeSF_LPs
select Sound Output_SF
Filter (pass Hann band)... 0 hpCutoff skirt
Rename... Output_SF_LP

#matchLPintensities
#select Sound Output_SF_LP
#Scale intensity... 'original_LP_intensity'

#blendHPportions
select Sound Output_SF_LP
Formula... self [col] + Sound_HP [col]
Rename... Output_SF_with_HPportion

#extractMiddleParts
select Sound Output_SF_with_HPportion
Extract part... start end rectangular 1 no
Rename... Output

#Play
Save as WAV file... 'outputSound$'
