# -*- coding: utf-8 -*-
"""
Created on Fri Mar 11 03:15:48 2011

@author: musselle
"""


import numpy as np
from numpy import dot, array, zeros, zeros_like
from numpy.linalg import qr
import numpy.matlib as npm
from matplotlib.pyplot import plot, figure, subplot, title, xlim, ylim, axvline, show, axhline
import os
import pickle as pk


def fmeasure(B, hits, misses, falses) :
    """ General formular for F measure 
    
    Uses TP(hits), FN(misses) and FP(falses)
    """
    x = ((1 + B**2) * hits) / ((1 + B**2) * hits + B**2 * misses + falses)
    return x

def analysis(res, ground_truths_tab, timesteps, epsilon = 0 , ignoreUpTo = 0 ):
    ''' Calculate all anomally detection Metrics 
    
    # epsilon: used to allow for lagged detections: if Anomaly occurs in time window
    anom_start - anom_end + eplsilon it is considered a TP
    
    # ignoreUpTo: does not count FPs before this time step
    
    '''
    # Detections  
    D = array(res['anomalies'])
    index =  D > ignoreUpTo 
    D = set(list(D[index]))        
    
    # Total Neg 
    total_negative = timesteps - ignoreUpTo - len(D)    
    
    # initalise metrics     
    metric = { 'TP' : 0.0 ,
               'FP' : 0.0 ,
               'FN' : 0.0 ,
               'precision' : 0.0 ,
               'recall' : 0.0 ,
               'F1' : 0.0 }
               
    # set of point anomalies detected as true
    anom_TP = set()
    
    # Set of anomalous segments detected           
    anom_segments_detected_set  = set()  
    # Table to record frequency of anomalous segment detections
    anomalies_detected_tab  = zeros_like(ground_truths_tab)
    anomalies_detected_tab[:,0] = ground_truths_tab[:,0]
    
    # TRUE POSITIVES
    # Run through ground truths 
    idx = 0
    for truth in ground_truths_tab:
        count = 0
        
        # Run through the list of detections    
        for d in D :
            if d >= truth[0]  and d <= truth[0] + truth[1] + epsilon:
                # if set does not yet contain the anomaly, add it and increment TP
                if not anom_segments_detected_set.issuperset(set([truth[0]])):
                    
                    anom_segments_detected_set.add(truth[0])
                    anom_TP.add(d)
                    metric['TP'] += 1
                    count += 1
                else: # if multiple detections in anomalous segment 
                    count += 1 
                    anom_TP.add(d)                    
                    
        anomalies_detected_tab[idx,1] = count   
        idx += 1     
    
    # FALSE Pos 
    anom_FP = D - anom_TP    
    metric['FP'] = len(anom_FP)
    
    # FALSE Neg     
    anom_FN = set(ground_truths_tab[:,0]) - anom_segments_detected_set
    metric['FN'] = len(anom_FN)
    
#    point anomalies
###########    
#    A = []
#    for line in ground_truths_tab :
#        for n in range(0,line[1]) :
#            A.append(line[0] + n)    
            
    #A = set(A)
    #anom_FN = A.difference(D)
    #metric['FN'] = len(anom_FN)
    
    metric['precision'] = metric['TP'] / (metric['TP'] + metric['FP'])
    metric['recall'] = metric['TP'] / (metric['TP'] + metric['FN'])    
    metric['FPR'] = metric['FP'] / total_negative
    metric['FDR'] = metric['FP'] / (metric['FP'] + metric['TP'])    
    metric['ACC'] = (metric['TP'] + total_negative - metric['FP'] )/  \
                    ( metric['TP'] + metric['FN'] + total_negative )
    metric['F1'] = fmeasure(1, metric['TP'], metric['FN'], metric['FP'])
    metric['F2'] = fmeasure(2, metric['TP'], metric['FN'], metric['FP'])
    metric['F05'] = fmeasure(0.5, metric['TP'], metric['FN'], metric['FP']) 
    
    sets = {'TP' : anom_TP,
            'anom_seg_detected' : anom_segments_detected_set,
            'FN' : anom_FN,
            'FP' : anom_FP}     
        
    return metric, sets, anomalies_detected_tab
    
def QRsolveA(A,b): # For arrays
    '''Solves equations of the type Ax = b by using A = QR ==> R * x = Q^T b ''' 
    Q, R = qr(A)
    cc = dot(Q.T , b)
    n = Q.shape[0]
    x = zeros((n,1))
    for j in range(n-1, -1, -1): # n-1, ....., 0
        if j != n-1:
            sum_rjk_xk = 0
            for k in range(j+1, n):
                sum_rjk_xk =  sum_rjk_xk + (R[j,k] * x[k])
            x[j] = (cc[j] - sum_rjk_xk) / R[j,j] 
        else:    
            x[j] = cc[j] / R[j,j]         
    return x
             
def QRsolveM(A,b): # for Matrices
    '''Solves equations of the type Ax = b by using A = QR ==> R * x = Q^T b ''' 
    Q, R = qr(A)
    cc = Q.T * b 
    n = Q.shape[0]
    x = npm.zeros((n,1))
    for j in range(n-1, -1, -1): # n-1, ....., 0
        if j != n-1:
            sum_rjk_xk = 0
            for k in range(j+1, n):
                sum_rjk_xk =  sum_rjk_xk + (R[j,k] * x[k])
            x[j] = (cc[j] - sum_rjk_xk) / R[j,j] 
        else:    
            x[j] = cc[j] / R[j,j]         
    return x  

def QRsolve_eigV(A,Z,h, Ut_1): # For arrays
    '''Estimates the eigenvalues of A and then solves equations of the type 
            Ax = b by using A = QR ==> R * x = Q^T b ''' 
   
    W = np.dot(A , Ut_1)
    
    U, R = np.linalg.qr(W)
    
    r = np.sqrt(Z) * np.dot(U.T , h) 
    
    # Now Rs = r ----> solve for s
    # Compact and faster back substitution 
    n = R.shape[0]
    s = np.zeros((n,1))
    for i in range(n-1,-1,-1):  # i=n:-1:-1  
        s[i] = (r[i] - np.dot(R[i, :],s)) / R[i, i]

    # The solution for Ax = b
    x = np.dot(Ut_1,s)
    # The eignevalue estimates for A
    e_values = R.diagonal()   
        
    return x, e_values, U
    
def pltSummary(res,data):
    ''' Three plot summary of results'''
    
    xmax = data.shape[0] 
    
    fig = figure()
    ax1 = fig.add_subplot(3,1,1)
    plot(data)
    title('Raw Data: - ' + res['Alg'])
    xlim(0, xmax)
    for x in res['anomalies']:
        axvline(x, ymin=0.25, color='r')
    
    fig.add_subplot(3,1,2, sharex = ax1)
    plot(res['hidden'])
    xlim(0, xmax)
    title('Hidden Variables')
    for x in res['anomalies']:
        axvline(x, ymin=0.75, color='r')    
    
    fig.add_subplot(3,1,3, sharex = ax1)
    plot(res['r_hist'])
    title('Subspace Rank')
    xlim(0, xmax)
    for x in res['anomalies']:
        axvline(x, ymin=0.75, color='r')
        
    fig.show() 

def pltSummary2(res,data,ethresh):
    ''' 4 plot summary of results'''
    
    xmax = data.shape[0] 
    
    fig = figure()
    ax1 = fig.add_subplot(4,1,1)
    plot(data)
    title('Raw Data: - ' + res['Alg'])
    xlim(0, xmax)
    for x in res['anomalies']:
        axvline(x, ymin=0.25, color='r')
    
    fig.add_subplot(4,1,2, sharex = ax1)
    plot(res['hidden'])
    xlim(0, xmax)
    title('Hidden Variables')
    for x in res['anomalies']:
        axvline(x, ymin=0.75, color='r')    
    
    fig.add_subplot(4,1,3, sharex = ax1)
    plot(res['r_hist'])
    title('Subspace Rank')
    xlim(0, xmax)
    for x in res['anomalies']:
        axvline(x, ymin=0.75, color='r')
        
    fig.add_subplot(4,1,4, sharex = ax1)
    plot(res['e_ratio'])
    title('Energy Ratio')
    xlim(0, xmax)
    for x in res['anomalies']:
        axvline(x, ymin=0.75, color='r')
    axhline(y=ethresh[0], ls = '--')
    axhline(y=ethresh[1], ls = '--')
    ylim(0.9, 1.05)
    
    fig.show()

    
def GetInHMS(seconds):
    ''' Return time in hours min and secs ''' 
    hours = seconds // 3600
    seconds -= 3600*hours
    minutes = seconds // 60
    seconds -= 60*minutes
    if hours == 0:
        return "%02dm:%02ds" % (minutes, seconds)
    return "%02dh:%02dm:%02ds" % (hours, minutes, seconds)
    
def writeRes(filename, resdict, parameters, dataFilename, path = '.', mode = 'w'):
    ''' Write Dictionary + parameters to txt file in pretty format '''
    cwd = os.getcwd()

    os.chdir(path)
    with open(filename, mode) as f :
        
        f.write('===========================================================\n')        
        f.write(dataFilename + '\n')
        f.write(parameters + '\n')
        f.write('-----------------------------------------------------------\n')
        for key, value in resdict.iteritems() :
            f.write('{0:9} ==>   {1:10s}'.format(key, value) + '\n')
        f.write('--\n')
    os.chdir(cwd) 
    
    
def write_3d_array2csv(filename, data):    
    
    # Write the array to disk
    with file(filename, 'w') as outfile:
        # I'm writing a header here just for the sake of readability
        # Any line starting with "#" will be ignored by numpy.loadtxt
        outfile.write('# Array shape: {0}\n'.format(data.shape))
    
        # Iterating through a ndimensional array produces slices along
        # the last axis. This is equivalent to data[i,:,:] in this case
        for data_slice in data:
    
            # The formatting string indicates that I'm writing out
            # the values in left-justified columns 7 characters in width
            # with 2 decimal places.  
            np.savetxt(outfile, data_slice, fmt='%-6.2f', delimiter = ', ')
    
            # Writing out a break to indicate different slices...
            outfile.write('# New slice\n')
            
def write2csv(E, metric, filename, header = 0):    
     
    data = E.R['met'][metric]
     
    # Write the array to disk
    with file(filename, 'w') as outfile:
        # I'm writing a header here just for the sake of readability
        # Any line starting with "#" will be ignored by numpy.loadtxt
        if header:
            outfile.write('# Array shape: {0}\n'.format(data.shape))
            outfile.write('# E.i: {0}\n'.format(E.i))
            outfile.write('# E.j: {0}\n'.format(E.j))
            outfile.write('# E.k: {0}\n'.format(E.k))
            outfile.write('\n')
            
        outfile.write('Values for {0} metric\n'.format(metric))
        outfile.write('\n')
            
        # Iterating through a ndimensional array produces slices along
        # the last axis. This is equivalent to data[i,:,:] in this case
            
        for i, data_slice in enumerate(data):
            
            outfile.write('Algorithm: {0}\n'.format(E.alg_ver[i]))
                
            # The formatting string indicates that I'm writing out
            # the values in left-justified columns 7 characters in width
            # with 2 decimal places.
            
            np.savetxt(outfile, data_slice, fmt='%-6d', delimiter = ', ')
            
            # Writing out a break to indicate different slices...
            outfile.write('\n')  

def combineMetrics(filename1, filename2, outfilename):    
    # Function to put FP and TP in one table 
    
    file1 = open(filename1, 'rb')
    file2 = open(filename2, 'rb')
    
    # Write the array to disk
    with file(outfilename, 'w') as outfile:        
        for line1 in file1:
            line2 = file2.readline()
            
            num1 = line1.split(',')
            num2 = line2.split(',')
            
            for i in range(len(num1)):
                if num1[i].find('.') != -1:
                    num1[i] = num1[i].split('.')[0]
                if num2[i].find('.') != -1:
                    num2[i] = num2[i].split('.')[0]
            
            if num1[0].strip().isdigit(): # Cheack if line contains numbers 
                
                l = []
                
                for i in range(len(num1)):
                    l.append(num1[i].strip() + ' / ' + num2[i].strip())
                
                newline = ','.join(l)
                outfile.write(newline + '\n')
            else:
                outfile.write(line1)
        
def clean_zeros(data, cpy = 0):
    """ Replaces points where data == 0 with the preceding value """
    
    if cpy:
        edited_data = data.copy()
    else:
        edited_data = data
        
    
    # run through each stream 
    for stream in range(edited_data.shape[1]):
        
        # Get zeroes indexs
        zeros_idx = edited_data[:,stream] == 0
        for idx, val in enumerate(zeros_idx):
            if val:
                # Replace with previous value
                edited_data[idx,stream] = edited_data[idx-1,stream]

    return edited_data

def npy2csv(infilename, outfilename):
    
    # Both parameters must be strings
    
    import csv 
    
    c = csv.writer(open(outfilename, "wb"))
    data = np.load(infilename)

    for row in data:
        c.writerow(row)
        
  
def zscore(data):
    """Returns z-score normalisation for each column of array"""

    zscore_data = np.zeros_like(data)
    timeSteps = data.shape[0]
    if data.ndim == 1:
        numStreams = 1
    else:
        numStreams = data.shape[1]

    # Clense of NaNs
    data = np.ma.MaskedArray(data, mask = np.isnan(data))

    for i in range(numStreams):
        zscore_data[:,i] = (data[:,i] - data[:,i].mean()) / data[:,i].std() 

    return zscore_data


def zscore_win(data, win_length):
    """Returns sliding window z-score normalisation for each column of array
    Note: nieve version. Could improve easily 
    """

    if data.ndim == 1:
        numStreams = 1
    else:
        numStreams = data.shape[1]


    if data.ndim == 1:
        window = np.zeros((1, win_length))
        zscore_data = np.zeros_like(data)
    else:
        window = np.zeros((data.shape[1], win_length))
        zscore_data = np.zeros_like(data)
        
    for i in range(data.shape[0]):
        # Shift Window
        window[:,:-1] = window[:,1:] 
        window[:,-1] = data[i]
        
        # Run function 
        est_mean_vec = window.mean(axis = 1)
        est_std_vec = window.std(axis = 1)
        zscore_data[i,:] =  (data[i,:] - est_mean_vec) / est_std_vec 
        
    return zscore_data

def RSRE(data, recon, ignored = 0):
    """Calaculate relative squared reconstruction error"""
    
    X_norm_sq = np.zeros(data.shape[0])    
    data_norm_sq = np.zeros(data.shape[0])
    
    for i in range(data.shape[0]):
        X_norm_sq[i] = np.linalg.norm(data[i,:] - recon[i,:]) ** 2
        data_norm_sq[i] = np.linalg.norm(data[i,:]) ** 2
    
        
    sum_x_norm_sq = X_norm_sq[ignored:].sum()
    sum_data_norm_sq = data_norm_sq[ignored:].sum()
    
    RSRE = sum_x_norm_sq / sum_data_norm_sq
    
    return RSRE 