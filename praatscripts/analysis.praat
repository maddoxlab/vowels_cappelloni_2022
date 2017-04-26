form Arguments
    sentence SourceFile
    sentence OutputGrid
endform

Read from file... 'sourceFile$'
Rename... SOURCE
To Formant (burg)... 0 5 5000 0.025 50
Down to FormantGrid
Save as short text file... 'outputGrid$'