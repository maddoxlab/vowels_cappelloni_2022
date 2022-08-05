#!/usr/bin/env python2
# -*- coding: utf-8 -*-
"""
Created on Sat Feb 25 19:13:20 2017

@author: vmateo
"""

import numpy as np
import os
import yaml
import matplotlib.pyplot as plt
import matplotlib.widgets as widget
from subprocess import Popen, PIPE
from sklearn.isotonic import isotonic_regression
from shutil import rmtree
from re import search
plt.ion()

# %% conversion formulas and helpers

def bark2hz(z):
    return 1960. * (0.53+z) / (26.28-z)

def hz2bark(f):
    return 26.81 * f / (1960.+f) - 0.53

def loadSettings(path):
    if os.path.isdir(path):
        path = os.path.join(path,'settings.yaml')
    with open(path,'r') as f:
        return yaml.load(f)

def saveSettings(path,data):
    with open(os.path.join(path,'settings.yaml'),'w') as f:
        yaml.dump(data,f)

def loadVowelData(talkerID,vowelID):
    return np.load(os.path.join('talkers',talkerID,vowelID,'data.npz'))

def saveVowelData(talkerID,vowelID,data):
    np.savez(os.path.join('talkers',talkerID,vowelID,'data.npz'),**data)

mypath = os.path.dirname(os.path.abspath(__file__))
settings = loadSettings('settings.yaml')

# %% data classes

#class rawData(dict):
#    def save(self,talkerID=self.talkerID,vowelID=self.vowelID):


# %% analysis and extraction step

def extractFramesAndRawFormantTracks(inputFile,talkerID,vowelID,
                                     outputFileFormat='img%03d.png',
                                     debug=False):
    talkerpath = os.path.join('talkers',talkerID)
    if not os.path.exists(talkerpath):
        os.mkdir(talkerpath)
    framespath = os.path.join(talkerpath,vowelID)
    if not os.path.exists(framespath):
        os.mkdir(framespath)

    gridName = os.path.join('tmp','tmp.FormantGrid')
    tempAudio = os.path.join('tmp','tmp.wav')

    #extract frames to PNG, audio to file
    args = [settings['ffmpeg'],
            '-i',
            inputFile,
#            '-pix_fmt','rgb24',
            os.path.join(framespath,outputFileFormat),
            '-y',
            os.path.join(tempAudio)]
    
    pipe = Popen(args,stdin = PIPE, stdout = PIPE, stderr = PIPE)
    _,err = pipe.communicate()
#    match = search(r"(\d*\.?\d*?) tbr",err)
#    framerate = float(match.group(1))
    framerate = 59.94

    saveSettings(framespath,{
            'image filename pattern':outputFileFormat,
            'framerate':framerate
            })

    #generate FormantGrid from audio file
    args = [settings['praat'],
            '--run',
            settings['analysis'],
            os.path.join(mypath,tempAudio),
            os.path.join(mypath,gridName)]
    
    pipe2 = Popen(args,stdin = PIPE, stdout = PIPE, stderr = PIPE)
    _,err2 = pipe2.communicate()

    #READ FORMANTGRID

    data = {}

    #open file and skip 5 lines
    grid = open(gridName,'r')
    for i in list(range(0,5)):
        print(grid.readline())
    #check number of formants
    if grid.readline() != '5\n':
        print('oops but its actually fine')

    #read formant tracks f1-f3
    for key in ['f1','f2','f3']:
        grid.readline()
        grid.readline()
        length = int(grid.readline())
        temp = np.empty((2,length))
        for i in range(0,length):
            temp[0][i] = float(grid.readline())
            temp[1][i] = float(grid.readline())
        temp[1] = hz2bark(temp[1])
        data[key] = temp

    #extract median values f4-f5
    for key in ['f4med','f5med']:
        grid.readline()
        grid.readline()
        length = int(grid.readline())
        temp = np.empty(length)
        for i in range(0,length):
            grid.readline()
            temp[i] = float(grid.readline())
        data[key] = hz2bark(np.median(temp))

    #check number of bandwidths
    if grid.readline() != '5\n':
        print('oops bandwidths')

    #extract bandwidths
    data['b'] = np.empty(5)
    for f in range(0,5):
        grid.readline()
        grid.readline()
        length = int(grid.readline())
        temp = np.empty(length)
        for i in range(0,length):
            grid.readline()
            temp[i] = float(grid.readline())
        data['b'][f] = np.median(temp)

    grid.close()

#    raw = rawData(data)
#    raw.talkerID = talkerID
#    raw.vowelID = vowelID

#    saveVowelData(talkerID,vowelID,data)
    if debug:
        return data,err,err2
    else:
        return data

def extractSourceAndHP(inputFile,talkerID,
                       hpCutoff=4000,skirt=500,lpcFreq=10000,lpcOrder=12):
    talkerpath = os.path.join('talkers',talkerID)
    if not os.path.exists(talkerpath):
        os.mkdir(talkerpath)
    if not os.path.isabs(inputFile):
        inputFile = os.path.join(mypath,inputFile)
    outputSource = os.path.join(mypath,talkerpath,'SOURCE.wav')
    outputHP = os.path.join(mypath,talkerpath,'HP.wav')

    args = [settings['praat'],
            '--run',
            settings['extraction'],
            inputFile,
            outputSource,
            outputHP,
            str(hpCutoff),
            str(skirt),
            str(lpcFreq),
            str(lpcOrder)]

    pipe = Popen(args,stdin = PIPE, stdout = PIPE, stderr = PIPE)
    _,err = pipe.communicate()

    saveSettings(talkerpath,{
            'hpCutoff':hpCutoff,
            'skirt':skirt
            })
    return err

# %% data editing

class TracksEditor:
    def display(self):
        for k in ['f1','f2','f3']:
            try:
                self.ax.lines.remove(self.lines[k])
                #fix color issues
            except KeyError:
                pass
            self.lines[k], = self.ax.plot(self.data[k][0],self.data[k][1],
                      color=self.colors[k],linestyle='solid',marker='o')
        self.ax.relim()
    def setData(self,data):
        self.data = dict(data)
    def setAxisLimits(self,left=None,right=None,bottom=None,top=None):
        self.ax.set_xlim(left,right)
        self.ax.set_ylim(bottom,top)
    def zoomReset(self):
        self.ax.autoscale()
    def eraseAxes(self):
        self.ax.clear()
        self.lines.clear()
        self.display()
        self.ax.set_autoscale_on(False)
    def __init__(self,data,flag=None,ax=None):
        if ax:
            self.ax = ax
        else:
            self.ax = plt.axes()
        self.colors = {'f1':'b','f2':'g','f3':'r'}
        self.lines = {}
        self.setData(data)
        self.display()
        self.ax.set_autoscale_on(False)

class TracksFitter(TracksEditor):
    def display(self):
        TracksEditor.display(self)
        for k in ['f1','f2','f3']:
            self.lines[k].linestyle = 'None'
            t = np.linspace(self.data[k][0][0],self.data[k][0][-1],500)
            self.ax.plot(t,np.polyval(self.fits[k],t),color=self.colors[k])
    def setData(self,data):
        TracksEditor.setData(self,data)
        self.fits = {}
        for k in ['f1','f2','f3']:
            self.fits[k] = np.polyfit(self.data[k][0],self.data[k][1],self.orders[k])
    def __init__(self,data,flag=None,ax=None):
        self.fits = {}
        self.orders = {'f1':3,'f2':3,'f3':3}
        TracksEditor.__init__(self,data,flag,ax)

class MyButton:
    def __init__(self,rect,text,func):
        self.ax = plt.axes(rect)
        self.button = widget.Button(self.ax,text)
        self.func = func
        self.cid = self.button.on_clicked(self.func)
    def __del__(self):
        plt.delaxes(self.ax)

def editTracks(data,iso_f2f3=True):
    vals = {'start':None,'end':None,'button':None,'rectOn':False}
    def funcMaker(i):
        def func(event,i=i):
            vals['button'] = i
        return func

    data = dict(data)
    fig,ax = plt.subplots()
    plt.subplots_adjust(bottom=0.2)
    editor = TracksEditor(data,ax=ax)

    buttonRects = {
#            'zoom1':[0.05,0.15,0.15,0.05],
            'zoom0':[0.025,0.1,0.175,0.05],
            'zoom1':[0.225,0.1,0.15,0.05],
            'next':[0.875,0.025,0.1,0.05],
            'del':[0.025,0.025,0.175,0.05],
            'trim':[0.225,0.025,0.15,0.05],
            }
    buttonTexts = {
            'zoom0':'View selection',
            'zoom1':'View all',
            'next':'Next',
            'del':'Delete range',
            'trim':'Auto trim'
            }
    buttons = {}
    for i in buttonRects.keys():
        buttons[i] = MyButton(buttonRects[i],buttonTexts[i],funcMaker(i))

    def rangeHelper(x1,x2):
        vals['start'] = x1
        vals['end'] = x2
    rangeSel = widget.SpanSelector(editor.ax,rangeHelper,'horizontal',span_stays=True)

    while True:
        if vals['button'] == 'zoom0':
            editor.setAxisLimits(vals['start'],vals['end'])
        elif vals['button'] == 'zoom1':
            editor.zoomReset()
        elif vals['button'] == 'del':
            for k in ['f1','f2','f3']:
                leftIndex = np.where(data[k][0]>=vals['start'])[0][0]
                rightIndex = np.where(data[k][0]<=vals['end'])[0][-1]
                data[k] = np.delete(data[k],np.arange(leftIndex,rightIndex+1),1)
            editor.setData(data)
            editor.display()
        elif vals['button'] == 'trim':
            minIndex = np.argmin(data['f1'][1])
            maxIndex = np.argmax(data['f1'][1])
            if minIndex < maxIndex: #ascending
                leftIndex = minIndex
                rightIndex = maxIndex
            else: #descending
                leftIndex = maxIndex
                rightIndex = minIndex
            start = data['f1'][0,leftIndex]
            end = data['f1'][0,rightIndex]
            data['f1'] = data['f1'][:,leftIndex:rightIndex+1]
            for k in ['f2','f3']:
                leftIndex = np.where(data[k][0]>=start)[0][0]
                rightIndex = np.where(data[k][0]<=end)[0][-1]
                data[k] = data[k][:,leftIndex:rightIndex+1]
            editor.setData(data)
            editor.display()
        elif vals['button'] == 'next':
            vals['button'] = None
            break
        vals['button'] = None
        plt.pause(1./60)
    del rangeSel
    editor.eraseAxes()
    del buttons['del'],buttons['trim']

    buttonRects = {
            'f1':[0.025,0.025,0.2,0.05],
            'f2':[0.25,0.025,0.2,0.05],
            'f3':[0.475,0.025,0.2,0.05]
            }
    buttonTexts = {
            'f1':'Delete f1 point(s)',
            'f2':'Delete f2 point(s)',
            'f3':'Delete f3 point(s)'
            }
    for i in buttonRects.keys():
        buttons[i] = MyButton(buttonRects[i],buttonTexts[i],funcMaker(i))

    def rectHelper(*args):
        vals['rectOn'] = True
    rectSel = widget.RectangleSelector(editor.ax,rectHelper,interactive=True)

    while True:
        if vals['rectOn'] and vals['button'] == 'zoom0':
            args = list(rectSel.extents)
            for i in [0,2]:
                if args[i] == args[i+1]:
                    args[i] = None
                    args[i+1] = None
            editor.setAxisLimits(*args)
        elif vals['button'] == 'zoom1':
            editor.zoomReset()
            #bug: if nothing has been deleted, this will zoom out to original
            #   data range
        elif vals['button'] in ['f1','f2','f3']:
            k = vals['button']
            left,right,bottom,top = rectSel.extents
            truthArray = np.logical_and(np.logical_and(np.logical_and(
                    data[k][0]>left,data[k][0]<right),
                    data[k][1]>bottom),
                    data[k][1]<top)
            indices = np.where(truthArray)
            data[k] = np.delete(data[k],indices,1)
            editor.setData(data)
            editor.display()
        elif vals['button'] == 'next':
            vals['button'] = None
            break
        vals['button'] = None
        plt.pause(1./60)

#    data['f1'] = isotonic(data['f1'])
#    data['mapping'],indices = generate_mapping(data['f1'])
#    data['f1'] = data['f1'][:,indices]

    editor.eraseAxes()
#    del editor
#    fitter = TracksFitter(data,ax=ax)

    return data

def isotonic(track):
    new = track[1]
    do_flip = new[0] > new[-1] #flip if decreasing
    if do_flip:
        new = new[::-1]
    new = isotonic_regression(new)
    if do_flip:
        new = new[::-1]
    return np.array([track[0],new])

def generate_mapping(f1,endpoints=None):
    if not endpoints:
        endpoints = [f1[1,0],f1[1][-1]]
    print(endpoints)
    temp,indices = np.unique(f1[1],return_index=True)
    print(temp, indices)
    if indices[0] > indices[1]:
        temp = temp[::-1]
        indices = indices[::-1]
    for i in range(len(indices)-1):
        indices[i] = (indices[i]+indices[i+1]-1)/2
    indices[-1] = (indices[-1]+len(f1[1])-1)/2

    r = endpoints[1]-endpoints[0]
    temp = temp - endpoints[0]
    temp = temp*1./r
    return np.array([temp,f1[0,indices]]),indices

def fix_data(data,iso_f2f3=True):
    data = dict(data)
    data['f1'] = isotonic(data['f1'])
    data['mapping'],indices = generate_mapping(data['f1'])
    data['f1'] = data['f1'][:,indices]
    if iso_f2f3:
        for f in ['f2','f3']:
            data[f] = isotonic(data[f])
            _,i = generate_mapping(data[f])
            data[f] = data[f][:,i]
    return data

# %% synthesis step

def synthesizeAudio(inputTrajectory,outputFile,talkerID,vowelID,start=0.,framerate=60.):
    time = np.arange(0,inputTrajectory.size)/float(framerate) + start
    end = time[-1]

    #declare filenames
    sourceSound = os.path.join(mypath,'talkers',talkerID,'SOURCE.wav')
    hpSound = os.path.join(mypath,'talkers',talkerID,'HP.wav')
    if not os.path.isabs(outputFile):
        outputFile = os.path.join(mypath,outputFile)
    gridName = os.path.join(mypath,'tmp','GRID.FormantGrid')

    data = loadVowelData(talkerID,vowelID)

    #interpolate new formant tracks
    t_temp = np.interp(inputTrajectory,data['mapping'][0],data['mapping'][1])
    outTracks = {}
    fkeys = ['f1','f2','f3']
    fkeys2 = ['f4med','f5med']
    bkey = 'b'
    for k in fkeys:
        outTracks[k] = bark2hz(np.interp(t_temp,data[k][0],data[k][1]))

    #get data for FormantGrid file
    talkerData = loadSettings(os.path.join('talkers',talkerID))
    hpCutoff = talkerData.get('hpCutoff',4000)
    skirt = talkerData.get('skirt',500)
    numFormants = 5
#    numFormants = 3

    #write FormantGrid file
    grid = open(gridName,'w')

    #header, number of formants
    grid.write('''File type = "ooTextFile"
    Object class = "FormantGrid"

    %f
    %f
    %d
    '''%(start,end,numFormants))

    #f1-f3 tracks
    for k in fkeys:
        numPoints = outTracks[k].shape[0]
        grid.write('%f\n%f\n%d\n'%(start,end,numPoints))
        for i in range(0,numPoints):
            grid.write('%f\n%f\n'%(time[i],outTracks[k][i]))

    #f4-f5 single value
    for k in fkeys2:
        numPoints = 1
        grid.write('%f\n%f\n%d\n'%(start,end,numPoints))
        grid.write('%f\n%f\n'%(start,bark2hz(data[k])))


    #bandwidths
    grid.write('%d\n'%(numFormants))
    for i in range(0,numFormants):
        numPoints = 1
        grid.write('%f\n%f\n%d\n'%(start,end,numPoints))
        grid.write('%f\n%f\n'%(start,data[bkey][i]))

    grid.close()
    data.close()

    #call Praat and return stdout, stderr messages
    args = [
            settings['praat'],
            '--run',
            settings['synthesis'],
            gridName,
            sourceSound,
            str(hpSound),
            str(hpCutoff),
            str(skirt),
            str(start),
            str(end),
            outputFile
            ]

    pipe = Popen(args,stdout = PIPE,stderr = PIPE,stdin = PIPE)
    _,err = pipe.communicate()

#    os.remove(gridName) #delete FormantGrid file
    return err

def synthesizeFrameIndices(inputTrajectory,talkerID,vowelID):
    data = loadVowelData(talkerID,vowelID)
    t_temp = np.interp(inputTrajectory,data['mapping'][0],data['mapping'][1])

    data.close()

    talkerData = loadSettings(os.path.join('talkers',talkerID,vowelID))
    firstStoredFrame = talkerData.pop('first image index',1)

    return (t_temp*talkerData['framerate'] + firstStoredFrame).astype(int)

def synthesizeVideo(inputTrajectory,outputFile,talkerID,vowelID,start=0.,framerate=60.):
    outputSound = os.path.join('tmp','video.wav')
    rmtree('tmp')
    os.mkdir('tmp')

    err = synthesizeAudio(inputTrajectory,outputSound,talkerID,vowelID,start,framerate)
    indices = synthesizeFrameIndices(inputTrajectory,talkerID,vowelID)

    talkerData = loadSettings(os.path.join('talkers',talkerID,vowelID))
    stem = talkerData['image filename pattern']
    tmpStem = os.path.join('tmp','tmp_%03d.png')

    for i in range(0,indices.size):
        os.symlink(os.path.join(mypath,'talkers',talkerID,vowelID,stem%indices[i]),tmpStem%i)

    command = [
            settings['ffmpeg'],
            '-framerate',str(framerate),
            '-i',tmpStem,
            '-i',outputSound,
            '-r',str(framerate),
#            '-pix_fmt','rgb24',
            '-y',
            '-c:v','libx264',
            '-crf','10',
            outputFile
            ]

    pipe = Popen(command,stdin=PIPE,stdout=PIPE,stderr=PIPE)
    _,err2 = pipe.communicate()

    return err,err2

# %% debugging

#data = loadVowelData('rosstalk','e-u_slow')
#f,i = generate_mapping(data['f1'])
