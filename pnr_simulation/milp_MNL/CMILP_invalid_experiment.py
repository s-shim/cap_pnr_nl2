import socket
import pandas as pd
import random 
from gurobipy import *
import math
import datetime
import time

# (numHubs,numAlternatives,numOrigins,numInstances) = (15,30,100,10)
machineName = socket.gethostname()

#(numHubs,numAlternatives,numOrigins,numInstances) = (15,30,100,10)
numInstances = 10
numDestins = 3 # fixed
tolError = 7 # limit of error of odds

grandAlternatives = pd.read_csv('pnr_list_corrected.csv')
grandIndividuals = pd.read_csv('pnr_utility_corrected.csv')

for (numAlternatives,numOrigins) in [(30,100),(60,200),(90,300),(120,400)]:

    numHubs = numAlternatives / 2
        
    machineArray = []
    originArray = []
    iArray = []
    jArray = []
    pArray = []
    instanceArray = []
    ilpObjArray = []
    accurateArray = []    
    unconstrainedArray = []
    underArray = []
    overArray = []
    runArray = []

    for instance in range(numInstances):
        print()
        print(datetime.datetime.now())
        print('### solve opt_constrained_invalid_pnr_origin%s_I%s_J%s_p%s_inst%s.csv'%(numOrigins,numOrigins*numDestins,numAlternatives,numHubs,instance))
    
        subAlternatives = pd.read_csv('./data/pnr_J%s_inst%s.csv'%(numAlternatives,instance))
        subIndividuals = pd.read_csv('./data/origin%s_I%s_inst%s.csv'%(numOrigins, numOrigins * numDestins, instance))
        
        pw = {} # preference weight
        for taz in subIndividuals['TAZ']:
            for destin in range(numDestins):
                j = 0 # j = 0 : car
                [utility] = grandIndividuals.loc[grandIndividuals['TAZ']==taz,'U_car_CBD%s'%(destin)]
                pw[taz,destin,j] = math.exp(utility)
        
        for taz in subIndividuals['TAZ']:
            for destin in range(numDestins):
                for j in subAlternatives['id']:
                    [utility] = grandIndividuals.loc[grandIndividuals['TAZ']==taz,'U_pnr_corr_%s_CBD_%s'%(j,destin)]
                    pw[taz,destin,j] = math.exp(utility)
        
        odds = {}
        for taz in subIndividuals['TAZ']:
            for destin in range(numDestins):
                for j in subAlternatives['id']:
                    odds[taz,destin,j] = pw[taz,destin,j] / pw[taz,destin,0]
                    
        Flow = {}
        for taz in subIndividuals['TAZ']:
            for destin in range(numDestins):
                [flow_i] = grandIndividuals.loc[grandIndividuals['TAZ']==taz,'car_to_CBD%s'%(destin)]
                Flow[taz,destin] = flow_i
        
        # ILP Model
        model = Model('pnr')
        setParam('LogFile', 'grblog_constrained_invalid_pnr_origin%s_I%s_J%s_p%s_inst%s_machine%s.txt'%(numOrigins,numOrigins*numDestins,numAlternatives,numHubs,instance,machineName))
        
        # Employ Variables
        y_vars = []
        y_names = []
        for j in subAlternatives['id']:
            y_vars += [(j)]
            y_names += ['Y[%s]'%(j)]
        Y = model.addVars(y_vars, vtype = GRB.BINARY, name = y_names)
        
        p_vars = []
        p_names = []
        for taz in subIndividuals['TAZ']:
            for destin in range(numDestins):
                p_vars += [(taz,destin,0)]
                p_names += ['P[%s,%s,%s]'%(taz,destin,0)]
                for j in subAlternatives['id']:
                    p_vars += [(taz,destin,j)]
                    p_names += ['P[%s,%s,%s]'%(taz,destin,j)]
        P = model.addVars(p_vars, vtype = GRB.CONTINUOUS, name = p_names)
                    
        # Add Constraints
        
        ## Given Number of Hubs
        LHS = []
        for j in subAlternatives['id']:
            LHS += [(1,Y[j])]
        model.addConstr(LinExpr(LHS)==numHubs, name='p-Hub')
                    
        ## P <= Y            
        for taz in subIndividuals['TAZ']:
            for destin in range(numDestins):
                for j in subAlternatives['id']:
                    LHS = [(1,P[taz,destin,j]),(-1,Y[j])]
                    model.addConstr(LinExpr(LHS)<=0, name='P<=Y[%s,%s,%s]'%(taz,destin,j))
                    
        ## Entire Probability = 1
        for taz in subIndividuals['TAZ']:
            for destin in range(numDestins):
                LHS = [(1,P[taz,destin,0])]
                for j in subAlternatives['id']:
                    LHS += [(1,P[taz,destin,j])]
                model.addConstr(LinExpr(LHS)==1, name='sumP=1[%s,%s]'%(taz,destin))
                
        ## 1. P[taz,destin,j] <= odds[taz,destin,j] * P[taz,destin,0]
        ## 2. P[taz,destin,0] <= 1 / odds[taz,destin,j] * P[taz,destin,j] + (1 - Y[j]) 
        for taz in subIndividuals['TAZ']:
            for destin in range(numDestins):
                for j in subAlternatives['id']:
        # =============================================================================
        #             LHS1 = [(-odds[taz,destin,j],P[taz,destin,0])]
        #             LHS1 += [(1,P[taz,destin,j])]
        #             model.addConstr(LinExpr(LHS1)<=0, name='choice<=base[%s,%s,%s]'%(taz,destin,j))
        # =============================================================================
        
                    if odds[taz,destin,j] > 10 ** (-tolError) and odds[taz,destin,j] < 10 ** tolError:
                        LHS1 = [(-odds[taz,destin,j],P[taz,destin,0])]
                        LHS1 += [(1,P[taz,destin,j])]
                        model.addConstr(LinExpr(LHS1)<=0, name='choice<=base[%s,%s,%s]'%(taz,destin,j))
            
                        #LHS2 = [(1,P[taz,destin,0])]
                        #LHS2 += [(- 1 / odds[taz,destin,j],P[taz,destin,j]),(1,Y[j])]
                        #model.addConstr(LinExpr(LHS2)<=1, name='choice>=base[%s,%s,%s]'%(taz,destin,j))
        
                    if odds[taz,destin,j] <= 10 ** (-tolError):
                        LHS1 = [(1,P[taz,destin,j])]
                        model.addConstr(LinExpr(LHS1)==0, name='choice<=base[%s,%s,%s]'%(taz,destin,j))
        
                    if odds[taz,destin,j] >= 10 ** tolError:
                        print('Too large an odds[taz,destin,j]=',odds[taz,destin,j])
                        
        # capacitate problem
        ## add additional variables
        w_vars = []
        w_names = []
        for j in subAlternatives['id']:
            w_vars += [(j)]
            w_names += ['W[%s]'%(j)]
        W = model.addVars(w_vars, vtype = GRB.CONTINUOUS, name = w_names)
        
        ## add additional constraints
        ### W[j] <= capacity of j
        for j in subAlternatives['id']:
            [capacity_j] = grandAlternatives.loc[grandAlternatives['id']==j,'capacity']
            LHS = [(1,W[j])]
            model.addConstr(LinExpr(LHS)<=capacity_j, name='W<=capacity[%s]'%(j))
        
        ### W[j] <= sum_taz sum_destin Flow[taz,destin] * P[taz,destin,j]
        for j in subAlternatives['id']:
            LHS = [(1,W[j])]
            for taz in subIndividuals['TAZ']:
                for destin in range(numDestins):
                    LHS += [(-Flow[taz,destin],P[taz,destin,j])]
            model.addConstr(LinExpr(LHS) <= 0, name='W<=Flow*P[%s]'%(j))
        
        # Set Objective
        objTerms = []
        for j in subAlternatives['id']:
            objTerms += [(1,W[j])]
        model.setObjective(LinExpr(objTerms), GRB.MAXIMIZE)
        
                    
        # update and solve the model
        model.update()
        #model = model.relax()
        model.optimize()
        
        
        variableName = []
        variableValue = []
        for v in model.getVars():
            variableName += [v.varname]
            variableValue += [v.x]
        
        optSolution = pd.DataFrame(list(zip(variableName, variableValue)),columns =['varName', 'varVal'])
        optSolution.to_csv(r'opt_constrained_invalid_pnr_origin%s_I%s_J%s_p%s_inst%s.csv'%(numOrigins,numOrigins*numDestins,numAlternatives,numHubs,instance), index = False)#Check
        
        unconstrainedVal = 0.0 
        underCapacity = 0
        overCapacity = 0
        theSelected = []            
        for j in subAlternatives['id']:
            [Y_j] = optSolution.loc[optSolution['varName']=='Y[%s]'%(j),'varVal']
            if Y_j > 1 - 0.0001:
                theSelected += [j]            
                [W_j] = optSolution.loc[optSolution['varName']=='W[%s]'%(j),'varVal']
                [capacity_j] = grandAlternatives.loc[grandAlternatives['id']==j,'capacity']
                expectedNum = 0.0
                for taz in subIndividuals['TAZ']:
                    for destin in range(numDestins):
                        [probability_ij] = optSolution.loc[optSolution['varName']=='P[%s,%s,%s]'%(taz,destin,j),'varVal']
                        expectedNum += Flow[taz,destin] * probability_ij

                unconstrainedVal += expectedNum 

                if expectedNum <= capacity_j:
                    print(j, expectedNum, capacity_j, 'under capacity', W_j)
                    underCapacity += 1
                else:
                    print(j, expectedNum, capacity_j, 'over capacity', W_j)
                    overCapacity += 1
        
        # demand(theSelected)
        totalPW = {}
        for taz in subIndividuals['TAZ']:
            for destin in range(numDestins):
                totalPW[taz,destin] = pw[taz,destin,0]
                for j in theSelected:
                    totalPW[taz,destin] += pw[taz,destin,j]
        
        totalDemand = 0.0
        for j in theSelected:
            demand_j = 0.0
            for taz in subIndividuals['TAZ']:
                for destin in range(numDestins):
                    demand_j += Flow[taz,destin] * pw[taz,destin,j] / totalPW[taz,destin]
            [capacity_j] = grandAlternatives.loc[grandAlternatives['id']==j,'capacity']
            totalDemand += min(demand_j,capacity_j)
            
        print('ILP OPT Val=',model.objVal)
        print('accurate=',totalDemand)
        print('underCapacity=',underCapacity)
        print('overCapacity=',overCapacity)

        machineArray += [machineName]
        originArray += [numOrigins]
        iArray += [numOrigins*numDestins]
        jArray += [numAlternatives]
        pArray += [numHubs]
        instanceArray += [instance]
        ilpObjArray += [model.objVal]
        accurateArray += [totalDemand]    
        unconstrainedArray += [unconstrainedVal]
        underArray += [underCapacity]
        overArray += [overCapacity]
        runArray += [model.Runtime]
        
        ilpTable = pd.DataFrame(list(zip(machineArray,originArray,iArray,jArray,pArray,instanceArray,ilpObjArray,accurateArray,unconstrainedArray,underArray,overArray,runArray)),columns =['Machine','Origins','I','J','p','instance','ILP OPT','Accuarate','ifUnconstrained','underCapacity','overCapacity','runTime'])
        ilpTable.to_csv(r'ilpTable_constrained_invalid_pnr_origin%s_I%s_J%s_p%s.csv'%(numOrigins,numOrigins*numDestins,numAlternatives,numHubs), index = False)#Check
    
            
