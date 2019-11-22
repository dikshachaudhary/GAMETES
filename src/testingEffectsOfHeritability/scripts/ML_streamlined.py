# Script name: ML_streamlined.py
# Author: Vivek Sriram, created using code written by Dr. Ryan J. Urbanowicz
# Last Revised: November 22nd, 2019
# ---------------------------------------------------------------------------
# Using datasets generated by GAMETES, this script will iterate over the set
# of files produced and run various feature importance selection algorithms
# as well as machine learners. It will then output results including accuracies
# for the various machine leaners, and lists of binary values stating whether
# or not the top trait(s) were identified. A range of heritabilities and dataset
# types are iterated over in this code.

import pandas as pd
import numpy as np
import scipy.stats as scs
import random
import time
import copy

from random import shuffle
import os

from scipy import interp
from scipy.stats import pearsonr
from sklearn.feature_selection import mutual_info_classif # Mutual information for a discrete target.
from sklearn.linear_model import LogisticRegression
from scipy.stats import norm
from sklearn import datasets
from sklearn.model_selection import train_test_split
from sklearn.metrics import roc_curve, auc

from sklearn.model_selection import GridSearchCV
from sklearn.ensemble import RandomForestClassifier
from sklearn import tree
import xgboost as xgb

from sklearn import metrics
from sklearn.metrics import r2_score
from sklearn.metrics import accuracy_score
from sklearn.metrics import balanced_accuracy_score
from sklearn.metrics import recall_score
from sklearn.metrics import confusion_matrix
from sklearn.metrics import classification_report
from sklearn.metrics import precision_score
from sklearn.metrics import f1_score

#Read from files
import glob

#Sort dictionaries
import operator


#ReliefF feature selection package
from skrebate import ReliefF
from skrebate import MultiSURF

#This code ensures that the output of plotting commands is displayed inline directly below the code cell that produced it.
import matplotlib.pyplot as plt
import seaborn as sb

#Import Progress bar
from tqdm import tnrange, tqdm_notebook

def mannWhitney(df, mwPositive, datasetType):
    mw_features = []
    mw_pValDict = {}

    for column in df:
        if not column == 'Class':
            #Univariate association test (Mann-Whitney Test - Non-parametric)
            c, p = scs.mannwhitneyu(x=df[column].loc[df['Class'] == 0],
                                    y=df[column].loc[df['Class'] == 1])

            #Identify and save features with 'significant' univariate association
            mw_pValDict[column] = [p]
            if p <= 0.05:
                mw_features.append(column)
    
    sortedPValueDict = sorted(mw_pValDict.items(), key=operator.itemgetter(1))
    #print(sortedPValueDict[0][0]) # Gets you the top key
    #print(sortedPValueDict[1][0]) # Gets you the second top key
    
    # If we're dealing with m1 or m2 as the input data
    if(len(datasetType) == 2):
        if(sortedPValueDict[0][0] == "M0P0"):
            mwPositive.append(1)
        else:
            mwPositive.append(0)
    
    # If we're dealing with m1m2Additive or m1m2Heterogeneous as the input data
    else:
        if(sortedPValueDict[0][0] == "M0P0" and sortedPValueDict[1][0] == "M1P0"):
            mwPositive.append(1)
        elif(sortedPValueDict[1][0] == "M0P0" and sortedPValueDict[0][0] == "M1P0"):
            mwPositive.append(1)
        else:
            mwPositive.append(0)
        
    return mwPositive


def pearsonCorrelation(df, pcPositive, datasetType):
    pc_features = []
    pc_pValDict = {}

    for column in df:
        if not column == 'Class':
            c, p = scs.pearsonr(x=df[column],y=df['Class'])

            #Identify and save features with 'significant' univariate association
            pc_pValDict[column] = [p]
            if p <= 0.05:
                pc_features.append(column)
    
    
    sortedPValueDict = sorted(pc_pValDict.items(), key=operator.itemgetter(1))

    # If we're dealing with m1 or m2 as the input data
    if(len(datasetType) == 2):
        if(sortedPValueDict[0][0] == "M0P0"):
            pcPositive.append(1)
        else:
            pcPositive.append(0)
    
    # If we're dealing with m1m2Additive or m1m2Heterogeneous as the input data
    else:
        if(sortedPValueDict[0][0] == "M0P0" and sortedPValueDict[1][0] == "M1P0"):
            pcPositive.append(1)
        elif(sortedPValueDict[1][0] == "M0P0" and sortedPValueDict[0][0] == "M1P0"):
            pcPositive.append(1)
        else:
            pcPositive.append(0)
    
    return pcPositive


def spearmanCorrelation(df, scPositive, datasetType):
    sc_features = []
    sc_pValDict = {}

    for column in df:
        if not column == 'Class':
            c, p = scs.spearmanr(a=df[column],b=df['Class'])

            #Identify and save features with 'significant' univariate association
            sc_pValDict[column] = [p]
            if p <= 0.05:
                sc_features.append(column)
                
    sortedPValueDict = sorted(sc_pValDict.items(), key=operator.itemgetter(1))

    # If we're dealing with m1 or m2 as the input data
    if(len(datasetType) == 2):
        if(sortedPValueDict[0][0] == "M0P0"):
            scPositive.append(1)
        else:
            scPositive.append(0)
    
    # If we're dealing with m1m2Additive or m1m2Heterogeneous as the input data
    else:
        if(sortedPValueDict[0][0] == "M0P0" and sortedPValueDict[1][0] == "M1P0"):
            scPositive.append(1)
        elif(sortedPValueDict[1][0] == "M0P0" and sortedPValueDict[0][0] == "M1P0"):
            scPositive.append(1)
        else:
            scPositive.append(0)
    
    return scPositive

def logit_pvalue(model, x):
    """ Calculate z-scores for scikit-learn LogisticRegression.
    parameters:
        model: fitted sklearn.linear_model.LogisticRegression with intercept and large C
        x:     matrix on which the model was fit
    This function uses asymtptics for maximum likelihood estimates.
    """
    p = model.predict_proba(x)
    n = len(p)
    m = len(model.coef_[0]) + 1
    coefs = np.concatenate([model.intercept_, model.coef_[0]])
    x_full = np.matrix(np.insert(np.array(x), 0, 1, axis = 1))
    ans = np.zeros((m, m))
    for i in range(n):
        ans = ans + np.dot(np.transpose(x_full[i, :]), x_full[i, :]) * p[i,1] * p[i, 0]
    vcov = np.linalg.inv(np.matrix(ans))
    se = np.sqrt(np.diag(vcov))
    t =  coefs/se  
    p = (1 - norm.cdf(abs(t))) * 2
    return p

def logisticRegression(df, lrPositive, datasetType):
    lr_features = []
    lr_pValDict = {}

    for column in tqdm_notebook(df, desc='1st loop'):  
        if not column == 'Class':
            x_ = df[column].values[:,np.newaxis]
            y_ = df['Class'].values
            clf = LogisticRegression(C=1e30,solver='lbfgs').fit(x_, y_)
            p = logit_pvalue(clf,x_)
        
            #Identify and save features with 'significant' univariate association
            lr_pValDict[column] = [p[1]]
            if p[1] <= 0.05:
                lr_features.append(column)
    
    sortedPValueDict = sorted(lr_pValDict.items(), key=operator.itemgetter(1))

    # If we're dealing with m1 or m2 as the input data
    if(len(datasetType) == 2):
        if(sortedPValueDict[0][0] == "M0P0"):
            lrPositive.append(1)
        else:
            lrPositive.append(0)
    
    # If we're dealing with m1m2Additive or m1m2Heterogeneous as the input data
    else:
        if(sortedPValueDict[0][0] == "M0P0" and sortedPValueDict[1][0] == "M1P0"):
            lrPositive.append(1)
        elif(sortedPValueDict[1][0] == "M0P0" and sortedPValueDict[0][0] == "M1P0"):
            lrPositive.append(1)
        else:
            lrPositive.append(0)
    
    return lrPositive

def mutualInformation(df, miPositive, datasetType):
    mi_pValDict = {}
    mi_features = []

    x_ = df.drop('Class', axis=1).values
    y_ = df['Class'].values

    #Run mutual information algorithm
    mi_results = mutual_info_classif(x_, y_)

    #Present results
    header = df.columns.tolist()
    header.remove('Class')

    counter = 0
    for each in mi_results:
        mi_pValDict[header[counter]] = each
        if each > 0: # Interesting MI score
            mi_features.append(header[counter])
        counter+=1

    sortedPValueDict = sorted(mi_pValDict.items(), key=operator.itemgetter(1))
    
    # If we're dealing with m1 or m2 as the input data
    if(len(datasetType) == 2):
        if(sortedPValueDict[len(sortedPValueDict)-1][0] == "M0P0"):
            miPositive.append(1)
        else:
            miPositive.append(0)
    
    # If we're dealing with m1m2Additive or m1m2Heterogeneous as the input data
    else:
        if(sortedPValueDict[len(sortedPValueDict)-1][0] == "M0P0" and sortedPValueDict[len(sortedPValueDict)-2][0] == "M1P0"):
            miPositive.append(1)
        elif(sortedPValueDict[len(sortedPValueDict)-2][0] == "M0P0" and sortedPValueDict[len(sortedPValueDict)-1][0] == "M1P0"):
            miPositive.append(1)
        else:
            miPositive.append(0)
    
    return miPositive

#Select a training subset for ReBATE
def reliefFeatureWeighting(df, rfPositive, datasetType):
    data_sample = df

    x_ = data_sample.drop('Class', axis=1).values
    y_ = data_sample['Class'].values

    start = time.clock()
    reliefF_results = ReliefF().fit(x_, y_) #ReliefF as a default 'k' hyperparameter that is set to 100 by default (i.e. 100 nearest neighbors)
    print(time.clock() - start, "seconds to run")

    rf_features = []
    rf_pValDict = {}

    #Present results
    header = df.columns.tolist()
    header.remove('Class')

    counter = 0
    for each in reliefF_results.feature_importances_:
        rf_pValDict[header[counter]] = each
        if each > 0: # Interesting MI score
            rf_features.append(header[counter])
        counter+=1
    
    sortedPValueDict = sorted(rf_pValDict.items(), key=operator.itemgetter(1))
   
    # If we're dealing with m1 or m2 as the input data
    if(len(datasetType) == 2):
        if(sortedPValueDict[len(sortedPValueDict)-1][0] == "M0P0"):
            rfPositive.append(1)
        else:
            rfPositive.append(0)
    
    # If we're dealing with m1m2Additive or m1m2Heterogeneous as the input data
    else:
        if(sortedPValueDict[len(sortedPValueDict)-1][0] == "M0P0" and sortedPValueDict[len(sortedPValueDict)-2][0] == "M1P0"):
            rfPositive.append(1)
        elif(sortedPValueDict[len(sortedPValueDict)-2][0] == "M0P0" and sortedPValueDict[len(sortedPValueDict)-1][0] == "M1P0"):
            rfPositive.append(1)
        else:
            rfPositive.append(0)
    
    return rfPositive

def decisionTree(randSeed, df, dtPositive, dtAccuracy, datasetType):
    param_grid = {"max_depth": [3, 6, None], "min_samples_split": [2,5,10],"min_samples_leaf": [1,5,10], 
              "criterion": ["gini", "entropy"]}
    
    dfVar = df.drop("Class", axis = 1)
    dfOut = df["Class"]
    featureNames = list(dfVar)
    
    ## 5-fold
    X_train1, X_test1, Y_train1, Y_test1 = train_test_split(dfVar, dfOut, test_size=0.20, random_state=42)
    X_train2, X_test2, Y_train2, Y_test2 = train_test_split(dfVar, dfOut, test_size=0.20, random_state=42)
    X_train3, X_test3, Y_train3, Y_test3 = train_test_split(dfVar, dfOut, test_size=0.20, random_state=42)
    X_train4, X_test4, Y_train4, Y_test4 = train_test_split(dfVar, dfOut, test_size=0.20, random_state=42)
    X_train5, X_test5, Y_train5, Y_test5 = train_test_split(dfVar, dfOut, test_size=0.20, random_state=42)
    xTrainList = [X_train1, X_train2, X_train3, X_train4, X_train5]
    yTrainList = [Y_train1, Y_train2, Y_train3, Y_train4, Y_train5]
    xTestList = [X_test1, X_test2, X_test3, X_test4, X_test5]
    yTestList = [Y_test1, Y_test1, Y_test1, Y_test1, Y_test1]
    
    sumOfPositives = 0
    sumOfAccuracies = 0
    
    for i in range(0, 5):
        x_train = xTrainList[i]
        y_train = yTrainList[i]
        x_test = xTestList[i]
        y_test = yTestList[i]

        #Run Hyperparameter sweep
        clf = tree.DecisionTreeClassifier(random_state = randSeed)
        search = GridSearchCV(estimator=clf, param_grid=param_grid, scoring='balanced_accuracy')
        search.fit(x_train, y_train)

        #Train model using 'best' hyperparameters - Uses default 3-fold internal CV (training/validation splits)
        clf = tree.DecisionTreeClassifier(random_state = randSeed, max_depth=search.best_params_['max_depth'],min_samples_split=search.best_params_['min_samples_split'],min_samples_leaf=search.best_params_['min_samples_leaf'], criterion=search.best_params_['criterion'])
        model = clf.fit(x_train, y_train)

        #Prediction evaluation
        yPred = clf.predict(x_test)
        sumOfAccuracies = sumOfAccuracies + accuracy_score(y_test, yPred)
    
        #obtain and store feature importance scores
        DTImp = clf.feature_importances_
        # Second element is top index, first element is the 2nd-top index
        top2Indices = sorted(range(len(DTImp)), key=lambda i: DTImp[i])[-2:]

        if(len(datasetType) == 2):
            if(featureNames[top2Indices[1]] == "M0P0"):
                sumOfPositives = sumOfPositives + 1
            
        # If we're dealing with m1m2Additive or m1m2Heterogeneous as the input data
        else:
            if(featureNames[top2Indices[0]] == "M0P0" and featureNames[top2Indices[1]] == "M1P0"):
                sumOfPositives = sumOfPositives + 1
            elif(featureNames[top2Indices[1]] == "M0P0" and featureNames[top2Indices[0]] == "M1P0"):
                sumOfPositives = sumOfPositives + 1
    
    return [round(sumOfPositives/5), sumOfAccuracies/5]

def randomForest(randSeed, df, randForestPositive, randForestAccuracy, datasetType):
    param_grid = {"max_depth": [3, 6, None], "min_samples_split": [2,5,10],"min_samples_leaf": [1,5,10], 
                  "criterion": ["gini", "entropy"],"n_estimators": [10,100,1000], "max_features": ['auto', 'log2']}
    
    #start = time.clock()

    dfVar = df.drop("Class", axis = 1)
    dfOut = df["Class"]
    featureNames = list(dfVar)
    
    x_train, x_test, y_train, y_test = train_test_split(dfVar, dfOut, test_size=0.20, random_state=42)
    
    sumOfPositives = 0
    sumOfAccuracies = 0
        
    #Run Hyperparameter sweep
    clf = RandomForestClassifier(random_state = randSeed)
    search = GridSearchCV(estimator=clf, n_jobs = -1, param_grid=param_grid, scoring='balanced_accuracy')
    search.fit(x_train, y_train)

    #Train model using 'best' hyperparameters - Uses default 3-fold internal CV (training/validation splits)
    clf = RandomForestClassifier(random_state = randSeed, n_jobs = -1, max_depth=search.best_params_['max_depth'], min_samples_split=search.best_params_['min_samples_split'],min_samples_leaf=search.best_params_['min_samples_leaf'], criterion=search.best_params_['criterion'],n_estimators=search.best_params_['n_estimators'],max_features=search.best_params_['max_features'])
    model = clf.fit(x_train, y_train)

    #Prediction evaluation
    yPred = clf.predict(x_test)

    #print(time.clock() - start, "seconds to run")

    sumOfAccuracies = sumOfAccuracies + accuracy_score(y_test, yPred)

    #obtain and store feature importance scores
    RFImp = clf.feature_importances_
    # Second element is top index, first element is the 2nd-top index
    top2Indices = sorted(range(len(RFImp)), key=lambda i: RFImp[i])[-2:]

    if(len(datasetType) == 2):
        if(featureNames[top2Indices[1]] == "M0P0"):
            sumOfPositives = sumOfPositives + 1
            
    # If we're dealing with m1m2Additive or m1m2Heterogeneous as the input data
    else:
        if(featureNames[top2Indices[0]] == "M0P0" and featureNames[top2Indices[1]] == "M1P0"):
            sumOfPositives = sumOfPositives + 1
        elif(featureNames[top2Indices[1]] == "M0P0" and featureNames[top2Indices[0]] == "M1P0"):
            sumOfPositives = sumOfPositives + 1
            
    return [sumOfPositives, sumOfAccuracies]

def xgBoost(randSeed, df, xgPositive, xgAccuracy, datasetType):
    param_grid = {'min_child_weight': [1, 5, 10],'gamma': [0, 1, 5],'subsample': [0.6, 0.8, 1.0],
                  'colsample_bytree': [0.6, 0.8, 1.0],'max_depth': [3, 6], 'learning_rate' : [0.01,0.3, 0.5]}

    dfVar = df.drop("Class", axis = 1)
    dfOut = df["Class"]
    featureNames = list(dfVar)
    
    ## 5-fold
    x_train, x_test, y_train, y_test = train_test_split(dfVar, dfOut, test_size=0.20, random_state=42)
    
    sumOfPositives = 0
    sumOfAccuracies = 0
    
    #Run Hyperparameter sweep
    clf = xgb.XGBClassifier(random_state = randSeed,nthread=-1)
    search = GridSearchCV(estimator=clf, param_grid=param_grid, scoring='balanced_accuracy')
    search.fit(x_train, y_train)

    #Train model using 'best' hyperparameters - Uses default 3-fold internal CV (training/validation splits)
    clf = xgb.XGBClassifier(random_state = randSeed,nthread=-1, min_child_weight=search.best_params_['min_child_weight'], 
    gamma=search.best_params_['gamma'], subsample=search.best_params_['subsample'], colsample_bytree=search.best_params_['colsample_bytree'],
    max_depth=search.best_params_['max_depth'],learning_rate=search.best_params_['learning_rate'])
    model = clf.fit(x_train, y_train)

    #Prediction evaluation
    yPred = clf.predict(x_test)
    sumOfAccuracies = sumOfAccuracies + accuracy_score(y_test, yPred)
        
    #obtain and store feature importance scores
    XGImp = clf.feature_importances_
    
    # Second element is top index, first element is the 2nd-top index
    top2Indices = sorted(range(len(XGImp)), key=lambda i: XGImp[i])[-2:]

    if(len(datasetType) == 2):
        if(featureNames[top2Indices[1]] == "M0P0"):
            sumOfPositives = sumOfPositives + 1
            
    # If we're dealing with m1m2Additive or m1m2Heterogeneous as the input data
    else:
        if(featureNames[top2Indices[0]] == "M0P0" and featureNames[top2Indices[1]] == "M1P0"):
            sumOfPositives = sumOfPositives + 1
        elif(featureNames[top2Indices[1]] == "M0P0" and featureNames[top2Indices[0]] == "M1P0"):
            sumOfPositives = sumOfPositives + 1
    
    return [sumOfPositives, sumOfAccuracies]


def saveToFile(famDir, heritabilityValue, dataset, inputData, outputName):
    outFilePath = str(famDir) + 'heritability_' + str(heritabilityValue) + '/' + str(dataset) + '_EDM-1/output/' + str(outputName) + '.txt'
    print("Writing to " + str(outputName))
    
    f=open(outFilePath,'w')
    f.write(str(inputData))
    f.close()

def main():
    print("Starting main!")
    randSeed = 42
    famDir = '/Users/viveksriram/Desktop/GAMETES-2.2/src/varyingHeritability/'

    #heritabilityRange = ["00", "10", "20", "30", "40", "50", "60", "70", "80", "90"]
    datasetOptions = ["m1", "m2", "m1m2Additive", "m1m2Heterogeneous"]
    #datasetOptions = ["m1m2Heterogeneous"]
    heritabilityRange = ["70", "80", "90"]
    #datasetOptions = ["m1m2Heterogeneous"]

    # Iterate over all possible heritabilities and dataset types
    for h in heritabilityRange:
        for d in datasetOptions:
            # For a given class of data and heritability, initialize empty output lists
            # Feature Selectors
            mwPositive = []
            pcPositive = []
            scPositive = []
            lrPositive = []
            miPositive = []
            rfPositive = []

            # Machine Learners
            dtPositive = []
            dtAccuracy = []
            randForestPositive = []
            randForestAccuracy = []
            xgPositive = []
            xgAccuracy = []

            # Get the input folder we'll be iterating over
            input_folder = str(famDir) + "heritability_" + str(h) + "/" + str(d) + "_EDM-1/data/"
            print("Working on heritability of 0." + str(h) + " and dataset " + str(d))
            
            # Get the files in our folder that correspond to data (i.e., start with "m1")
            files = [f for f in glob.glob(input_folder + "**/*.txt", recursive=True)]
            files.sort()

            i = 1    
            # For each dataset, update our lists of values for each of our feature selection algorithms and each of our learning classifiers
            for f in files:
                df = pd.read_csv(f, sep="\t")
                print("On " + str(i) + "th dataset")
                #print(str(f))
                
                #mwPositive = mannWhitney(df, mwPositive, d)
                #pcPositive = pearsonCorrelation(df, pcPositive, d)
                #scPositive = spearmanCorrelation(df, scPositive, d)
                #lrPositive = logisticRegression(df, lrPositive, d)
                #miPositive = mutualInformation(df, miPositive, d)
                #rfPositive = reliefFeatureWeighting(df, rfPositive, d)
                
                #dtOutput = decisionTree(randSeed, df, dtPositive, dtAccuracy, d)
                #dtPositive.append(dtOutput[0])
                #dtAccuracy.append(dtOutput[1])
        
                #randForestOutput = randomForest(randSeed, df, randForestPositive, randForestAccuracy, d)
                #randForestPositive.append(randForestOutput[0])
                #randForestAccuracy.append(randForestOutput[1])
        
                xgOutput = xgBoost(randSeed, df, xgPositive, xgAccuracy, d)
                xgPositive.append(xgOutput[0])
                xgAccuracy.append(xgOutput[1])

                if(i == 30):
                    break
                i = i+1
                    
            # Save lists to output files
            #saveToFile(famDir, h, d, mwPositive, "mwOutput")
            #saveToFile(famDir, h, d, pcPositive, "pcOutput")
            #saveToFile(famDir, h, d, scPositive, "scOutput")
            #saveToFile(famDir, h, d, lrPositive, "lrOutput")
            #saveToFile(famDir, h, d, miPositive, "miOutput")
            #saveToFile(famDir, h, d, rfPositive, "rfOutput")
            #saveToFile(famDir, h, d, dtPositive, "dtPositiveOutput")
            #saveToFile(famDir, h, d, dtAccuracy, "dtAccuracyOutput")
            #saveToFile(famDir, h, d, randForestPositive, "randForestPositiveOutput")
            #saveToFile(famDir, h, d, randForestAccuracy, "randForestAccuracyOutput")
            saveToFile(famDir, h, d, xgPositive, "xgPositiveOutput")
            saveToFile(famDir, h, d, xgAccuracy, "xgAccuracyOutput")

if __name__ == "__main__":
    main()