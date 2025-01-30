import pandas as pd
import random 
import math
import copy
import time
import datetime
import socket
import multiprocessing as mp


# Front Matter: Define functions
def ARR_Capacitated(coreID,timeLimit,lambdaNL,tolError,instance,numHubs,numAlternatives,numOrigins,numDestins,grandAlternatives,grandIndividuals,machineName,subAlternatives,subIndividuals):
   
    util = {}
    for taz in subIndividuals['TAZ']:
        for destin in range(numDestins):
            j = 0 # j = 0 : car
            [utility] = grandIndividuals.loc[grandIndividuals['TAZ']==taz,'U_car_CBD%s'%(destin)]
            util[taz,destin,j] = float(utility) 
    
    for taz in subIndividuals['TAZ']:
        for destin in range(numDestins):
            for j in subAlternatives['id']:
                [utility] = grandIndividuals.loc[grandIndividuals['TAZ']==taz,'U_pnr_corr_%s_CBD_%s'%(j,destin)]
                util[taz,destin,j] = float(utility) 
                
    Flow = {}
    for taz in subIndividuals['TAZ']:
        for destin in range(numDestins):
            [flow_i] = grandIndividuals.loc[grandIndividuals['TAZ']==taz,'car_to_CBD%s'%(destin)]
            Flow[taz,destin] = flow_i
    
    halfY = {}
    for j in subAlternatives['id']:
        halfY[j] = 0.5
        
    tic = time.time()
    # seed -> perturb     
    seedY = copy.deepcopy(halfY)
    ptbY = {}
    for j in subAlternatives['id']:
        ptbY[j] = seedY[j] * random.random()
    
    
    # theSelected = ROUND(ptb)
    theSelected = []
    jToProcess = copy.deepcopy(list(subAlternatives['id']))
    while len(theSelected) < numHubs:
        largest = 0.0    
        largestJ = -1
        for j in jToProcess:
            if largest < ptbY[j]:
                largest = ptbY[j]
                largestJ = j
        jToProcess.remove(largestJ)
        theSelected += [largestJ]
    
    
    # demand(theSelected)
    totalPW_PNR_NL = {}
    for taz in subIndividuals['TAZ']:
        for destin in range(numDestins):
            totalPW_PNR_NL[taz,destin] = 0.0
            for j in theSelected:
                totalPW_PNR_NL[taz,destin] += math.exp(util[taz,destin,j]/lambdaNL)
    
    gamma = {}
    for taz in subIndividuals['TAZ']:
        for destin in range(numDestins):
            gamma[taz,destin] = 0.0 # compute gamma_i
            for j in theSelected:
                gamma[taz,destin] += math.exp(util[taz,destin,j]/lambdaNL)
            gamma[taz,destin] = math.log(gamma[taz,destin])
            
    totalDemand = 0.0
    for j in theSelected:
        demand_j = 0.0
        for taz in subIndividuals['TAZ']:
            for destin in range(numDestins):
                demand_j += Flow[taz,destin] * (math.exp(lambdaNL * gamma[taz,destin]) / (math.exp(util[taz,destin,0]) + math.exp(lambdaNL * gamma[taz,destin]))) * (math.exp(util[taz,destin,j]/lambdaNL) / totalPW_PNR_NL[taz,destin])
        [capacity_j] = grandAlternatives.loc[grandAlternatives['id']==j,'capacity']
        totalDemand += min(demand_j,capacity_j) # capacitated
        #totalDemand += demand_j # unconstrained
                            
    
    # record trial = 0
    bestDemand = totalDemand
    bestSelected = copy.deepcopy(sorted(theSelected))
    trial = 0
    nLocal = 0
    reset = False
    toc = time.time()
    #print()
    #print('trial=',trial)
    #print('elapse time=',toc-tic)
    #print('bestDemand=',bestDemand)
    
    machineArray = [machineName]
    lambdaArray = [lambdaNL]
    trialArray = [trial]
    timeArray = [toc-tic]
    demandArray = [bestDemand]
    
    selectedArray = {}
    for num in range(numHubs):
        selectedArray[num] = [bestSelected[num]]
    
    bestSolution = pd.DataFrame(list(zip(machineArray,trialArray,timeArray,demandArray)),columns =['Machine','Trial','Time','Demand'])
    for num in range(numHubs):
        bestSolution['selectedHub%s'%num] = selectedArray[num] 
    
    # bestSolution.to_csv(r'result/origin%s/arr_constrainedNL_pnr_origin%s_I%s_J%s_p%s_inst%s_lambda(%s)_Core%s.csv'%(numOrigins,numOrigins,numOrigins*numDestins,numAlternatives,numHubs,instance,int(lambdaNL*100),coreID), index = False)#Check
    bestSolution.to_csv(r'result/origin%s_small/arr_constrainedNL_pnr_origin%s_I%s_J%s_p%s_inst%s_lambda(%s)_Core%s.csv'%(numOrigins,numOrigins,numOrigins*numDestins,numAlternatives,numHubs,instance,int(lambdaNL*100),coreID), index = False)#Check
    
    toc = time.time()
    elapseTime = toc - tic
    bestTime = toc - tic
    bestTrial = trial
    while elapseTime < timeLimit:
        
        trial += 1
    
        # compute RMSD
        RMSD = 0.0
        for j in subAlternatives['id']:
            RMSD += (seedY[j] - 0.5) ** 2
        RMSD = math.sqrt(RMSD / len(subAlternatives['id']))
    
        # seed -> perturb     
        ptbY = {}
        for j in subAlternatives['id']:
            ptbY[j] = seedY[j] * random.random()
        
        # theSelected = ROUND(ptb)
        theSelected = []
        jToProcess = copy.deepcopy(list(subAlternatives['id']))
        while len(theSelected) < numHubs:
            largest = 0.0    
            largestJ = -1
            for j in jToProcess:
                if largest < ptbY[j]:
                    largest = ptbY[j]
                    largestJ = j
            jToProcess.remove(largestJ)
            theSelected += [largestJ]
            
            
        # check theSelected = bestSelected
        same = True
        for j in bestSelected:
            if j not in theSelected:
                same = False
                break
            
        if same == True:
            nLocal += 1
            
            # compute reset probability
            ## pR = probability of reset
            pR = min(1,nLocal/20) * RMSD
            if pR > random.random():
                reset = True
                seedY = copy.deepcopy(halfY)
                nLocal = 0
                
        else:
            nLocal = 0
            reset = False
            
            # demand(theSelected)
            totalPW_PNR_NL = {}
            for taz in subIndividuals['TAZ']:
                for destin in range(numDestins):
                    totalPW_PNR_NL[taz,destin] = 0.0
                    for j in theSelected:
                        totalPW_PNR_NL[taz,destin] += math.exp(util[taz,destin,j]/lambdaNL)
            
            gamma = {}
            for taz in subIndividuals['TAZ']:
                for destin in range(numDestins):
                    gamma[taz,destin] = 0.0 # compute gamma_i
                    for j in theSelected:
                        gamma[taz,destin] += math.exp(util[taz,destin,j]/lambdaNL)
                    gamma[taz,destin] = math.log(gamma[taz,destin])
                    
            totalDemand = 0.0
            for j in theSelected:
                demand_j = 0.0
                for taz in subIndividuals['TAZ']:
                    for destin in range(numDestins):
                        demand_j += Flow[taz,destin] * (math.exp(lambdaNL * gamma[taz,destin]) / (math.exp(util[taz,destin,0]) + math.exp(lambdaNL * gamma[taz,destin]))) * (math.exp(util[taz,destin,j]/lambdaNL) / totalPW_PNR_NL[taz,destin])
                [capacity_j] = grandAlternatives.loc[grandAlternatives['id']==j,'capacity']
                totalDemand += min(demand_j,capacity_j) # capacitated
                #totalDemand += demand_j # unconstrained
                
                
            if bestDemand < totalDemand:
                bestDemand = totalDemand
                bestSelected = copy.deepcopy(sorted(theSelected))            
                print()
                print('trial=',trial)
                toc=time.time()
                print('elapse time=',toc-tic)
                print('bestDemand=',bestDemand)
                bestTime = toc - tic
                bestTrial = trial
    
                machineArray += [machineName]
                lambdaArray += [lambdaNL]
                trialArray += [trial]
                timeArray += [toc-tic]
                demandArray += [bestDemand]
                
                for num in range(numHubs):
                    selectedArray[num] += [bestSelected[num]]
                
                bestSolution = pd.DataFrame(list(zip(machineArray,lambdaArray,trialArray,timeArray,demandArray)),columns =['Machine','Lambda','Trial','Time','Demand'])
                for num in range(numHubs):
                    bestSolution['selectedHub%s'%num] = selectedArray[num] 
                
                # bestSolution.to_csv(r'result/origin%s/arr_constrainedNL_pnr_origin%s_I%s_J%s_p%s_inst%s_lambda(%s)_Core%s.csv'%(numOrigins,numOrigins,numOrigins*numDestins,numAlternatives,numHubs,instance,int(lambdaNL*100),coreID), index = False)#Check
                bestSolution.to_csv(r'result/origin%s_small/arr_constrainedNL_pnr_origin%s_I%s_J%s_p%s_inst%s_lambda(%s)_Core%s.csv'%(numOrigins,numOrigins,numOrigins*numDestins,numAlternatives,numHubs,instance,int(lambdaNL*100),coreID), index = False)#Check
            
        if reset == False:
            alpha = 1 / (1 + math.exp(4 * RMSD))
            for j in subAlternatives['id']:
                seedY[j] = (1 - alpha) * seedY[j]
            for j in bestSelected:
                seedY[j] += alpha 
            
        toc = time.time()
        elapseTime = toc - tic
    
    return coreID,elapseTime,bestDemand,bestSelected,bestTime,bestTrial


def ARR_Capacitated2(args):
    coreID,timeLimit,lambdaNL,tolError,instance,numHubs,numAlternatives,numOrigins,numDestins,grandAlternatives,grandIndividuals,machineName,subAlternatives, subIndividuals = args
    return ARR_Capacitated(coreID,timeLimit,lambdaNL,tolError,instance,numHubs,numAlternatives,numOrigins,numDestins,grandAlternatives,grandIndividuals,machineName,subAlternatives,subIndividuals)



# Code starts here
# Read Data
grandAlternatives = pd.read_csv('pnr_list_corrected.csv')
grandIndividuals = pd.read_csv('pnr_utility_corrected.csv')
numDestins = 3 # fixed
tolError = 7 # limit of error of odds
timeLimit = 60 * 60 * 15
instance = 0


subAlternatives = pd.read_csv('pnr_list_corrected.csv')
subIndividuals = pd.read_csv('pnr_utility_corrected.csv')

lambdaNL = 0.25 # [1,0.5,0.75,0.25]:
numAlternatives = len(subAlternatives['id'])
numOrigins = len(subIndividuals['TAZ'])


for numHubs in [80,40,20]:

    print()
    print('### Capacitated')
    machineName = socket.gethostname()
    print(machineName,lambdaNL,instance,numHubs,numAlternatives,numOrigins,numDestins,timeLimit)
    print(datetime.datetime.now())

    if __name__ == '__main__':
        numCores = mp.cpu_count()
        p = mp.Pool(numCores)
    
        multiArgs = []  
        for coreID in range(numCores):
            multiArgs += [(coreID,timeLimit,lambdaNL,tolError,instance,numHubs,numAlternatives,numOrigins,numDestins,grandAlternatives,grandIndividuals,machineName,subAlternatives,subIndividuals)]  
    
        results = p.map(ARR_Capacitated2, multiArgs)
    
        machineArray = [] 
        coreArray = []
        instanceArray = []
        numHubsArray = []
        numAlternativesArray = []
        numOriginsArray = []
        numDestinsArray = []
        tolErrorArray = []
        lambdaArray = []
        timeLimitArray = []
        timeArray = []
        bestTimeArray = []
        trialArray = []
        demandArray = []        
        bestSelectedArray = {}
        for num in range(numHubs):
            bestSelectedArray[num] = []

        for coreID0,elapseTime0,bestDemand0,bestSelected0,bestTime0,bestTrial0 in results:
            machineArray += [machineName]
            coreArray += [coreID0]
            instanceArray += [instance]
            numHubsArray += [numHubs]
            numAlternativesArray += [numAlternatives]
            numOriginsArray += [numOrigins]
            numDestinsArray += [numDestins]
            tolErrorArray += [10 ** (-tolError)]
            lambdaArray += [lambdaNL]
            timeLimitArray += [timeLimit]
            timeArray += [elapseTime0]
            bestTimeArray += [bestTime0]
            trialArray += [bestTrial0]
            demandArray += [bestDemand0]
            for num in range(numHubs):
                bestSelectedArray[num] += [bestSelected0[num]]
    
            #print(coreID0,elapseTime0,bestDemand0,bestSelected0,bestTime0,bestTrial0)
    
    
            listZip = list(zip(machineArray,coreArray,instanceArray,numHubsArray,numAlternativesArray,numOriginsArray,numDestinsArray,tolErrorArray,lambdaArray,timeLimitArray,timeArray,bestTimeArray,trialArray,demandArray))
            grandResult = pd.DataFrame(listZip,columns =['Machine','Core','Instance','Hubs','Alternatives','Origins','Destins','tolError','logSum','Time Limit','Elapse Time','Best Time','Best Trial','Best Demand'])
            for num in range(numHubs):
                grandResult['selectedHub%s'%num] = bestSelectedArray[num] 
            grandResult.to_csv(r'result/result_constrainedNL_pnr_origin%s_I%s_J%s_p%s_inst%s_lambda(%s)_numCores%s.csv'%(numOrigins,numOrigins*numDestins,numAlternatives,numHubs,instance,int(lambdaNL*100),numCores), index = False)#Check
    
