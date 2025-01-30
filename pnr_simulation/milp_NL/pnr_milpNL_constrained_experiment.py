import pandas as pd
import random 
from gurobipy import *
import math
import datetime
import socket
import copy

machineName = socket.gethostname()
warmStart = False
timeLimit = False

for (numAlternatives,numOrigins,TL) in [(30,100,300)]:# [(30,100,300),(60,200,600),(90,300,1800),(120,400,3600)]:
    for logSum in [1,0.5,0.75,0.25]:
        for strong in [False]:#[True,False]:

            numHubs = int(numAlternatives / 2)
                
            machineArray = []
            warmArray = []
            logSumArray = []
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
            countArray = []
            
            for instance in range(10):
                grandAlternatives = pd.read_csv('pnr_list_corrected.csv')
                grandIndividuals = pd.read_csv('pnr_utility_corrected.csv')
                numDestins = 3 # fixed
                tolError = 7 # limit of error of odds
                
                subAlternatives = pd.read_csv('./data/pnr_J%s_inst%s.csv'%(numAlternatives,instance))
                subIndividuals = pd.read_csv('./data/origin%s_I%s_inst%s.csv'%(numOrigins, numOrigins * numDestins, instance))
                
                pw = {} # preference weight
                for taz in subIndividuals['TAZ']:
                    for destin in range(numDestins):
                        j = 0 # j = 0 : car
                        [utility] = grandIndividuals.loc[grandIndividuals['TAZ']==taz,'U_car_CBD%s'%(destin)]
                        pw[taz,destin,j] = math.exp(utility)
                
                pwadj = {} # preference weight adjusted
                vanish = {}
                candidate = {}
                for taz in subIndividuals['TAZ']:
                    for destin in range(numDestins):
                        vanish[taz,destin] = []
                        candidate[taz,destin] = []
                        for j in subAlternatives['id']:
                            [utility] = grandIndividuals.loc[grandIndividuals['TAZ']==taz,'U_pnr_corr_%s_CBD_%s'%(j,destin)]
                            pw[taz,destin,j] = math.exp(utility)
                            #print(taz,destin,j,pw[taz,destin,j] / pw[taz,destin,0])
                            if pow(pw[taz,destin,j] / pw[taz,destin,0], 1 / logSum) < pow(10,-tolError):
                                pwadj[taz,destin,j] = 0
                                vanish[taz,destin] += [j]
                            else:
                                pwadj[taz,destin,j] = pw[taz,destin,j] / pw[taz,destin,0]
                                candidate[taz,destin] += [j]
                
                pwa = {} # preference weight to logSum power
                for taz in subIndividuals['TAZ']:
                    for destin in range(numDestins):
                        pwa[taz,destin,0] = 1
                        for j in candidate[taz,destin]:
                            pwa[taz,destin,j] = pow(pwadj[taz,destin,j], 1 / logSum)
                        for j in vanish[taz,destin]:
                            pwa[taz,destin,j] = 0
                
                Flow = {}
                for taz in subIndividuals['TAZ']:
                    for destin in range(numDestins):
                        [flow_i] = grandIndividuals.loc[grandIndividuals['TAZ']==taz,'car_to_CBD%s'%(destin)]
                        Flow[taz,destin] = flow_i
                
                print(datetime.datetime.now())
                print()
                print('### START')
                print('Solve opt_constrainedNL_logSum%s_pnr_origin%s_I%s_J%s_p%s_inst%s.csv'%(int(logSum*100),numOrigins,numOrigins*numDestins,numAlternatives,numHubs,instance))
                print('Warmstart =',warmStart)
                
                # ILP Model
                model = Model('pnr')
                
                setParam('LogFile', 'result/origin%s/grblog_constrainedNL_warm%s_logSum%s_pnr_origin%s_I%s_J%s_p%s_inst%s_machine%s.txt'%(numOrigins,warmStart,int(logSum*100),numOrigins,numOrigins*numDestins,numAlternatives,numHubs,instance,machineName))
                if timeLimit == True:
                    setParam('TimeLimit',TL)
                
                ## Employ Variables
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
                
                ## Add Constraints
                ### Given Number of Hubs
                LHS = []
                for j in subAlternatives['id']:
                    LHS += [(1,Y[j])]
                model.addConstr(LinExpr(LHS)==numHubs, name='p-Hub')
                
                ## Entire Probability = 1
                for taz in subIndividuals['TAZ']:
                    for destin in range(numDestins):
                        LHS = [(1,P[taz,destin,0])]
                        for j in subAlternatives['id']:
                            LHS += [(1,P[taz,destin,j])]
                        model.addConstr(LinExpr(LHS)==1, name='sumP=1[%s,%s]'%(taz,destin))
                
                ### P <= Y            
                if strong == False:
                    for taz in subIndividuals['TAZ']:
                        for destin in range(numDestins):
                            for j in subAlternatives['id']:
                                LHS = [(1,P[taz,destin,j]),(-1,Y[j])]
                                model.addConstr(LinExpr(LHS)<=0, name='P<=Y[%s,%s,%s]'%(taz,destin,j)) 
                if strong == True:
                    for taz in subIndividuals['TAZ']:
                        for destin in range(numDestins):                        
                            for j in subAlternatives['id']:
    
                                set_j = copy.deepcopy(list(subAlternatives['id']))
                                set_j.remove(j)
                                minSet_j = []
                                maxSet_j = []
                                for k in set_j:
                                    minSet_j += [pwa[taz,destin,k]]
                                    maxSet_j += [pwa[taz,destin,k]]
                                    
                                minSet_j.sort()
                                maxSet_j.sort(reverse=True)
                                
                                totalPWA_j_min = pwa[taz,destin,j]
                                totalPWA_j_max = pwa[taz,destin,j]
                                for num_j in range(numHubs-1):
                                    totalPWA_j_min += minSet_j[num_j]
                                    totalPWA_j_max += maxSet_j[num_j]
                                    
                                if j not in vanish[taz,destin]:
                                    if totalPWA_j_min > pow(10,-tolError):
                                        p_min = pow(totalPWA_j_min,logSum) / (1 + pow(totalPWA_j_min,logSum)) * pwa[taz,destin,j] / totalPWA_j_max 
                                        p_max = pow(totalPWA_j_max,logSum) / (1 + pow(totalPWA_j_max,logSum)) * pwa[taz,destin,j] / totalPWA_j_min 
                                        
                                        LHS_min = [(-1,P[taz,destin,j]),(p_min,Y[j])]
                                        model.addConstr(LinExpr(LHS_min)<=0, name='P_min[%s,%s,%s]'%(taz,destin,j)) 
            
                                        LHS_max = [(-1,P[taz,destin,j]),(p_max,Y[j])]
                                        model.addConstr(LinExpr(LHS_max)>=0, name='P_max[%s,%s,%s]'%(taz,destin,j)) 
                                    else:
                                        LHS = [(1,P[taz,destin,j]),(-1,Y[j])]
                                        model.addConstr(LinExpr(LHS)<=0, name='P<=Y[%s,%s,%s]'%(taz,destin,j)) 
                
                ## capacitate problem
                ### add additional variables
                w_vars = []
                w_names = []
                for j in subAlternatives['id']:
                    w_vars += [(j)]
                    w_names += ['W[%s]'%(j)]
                W = model.addVars(w_vars, vtype = GRB.CONTINUOUS, name = w_names)
                
                ### add additional constraints
                #### W[j] <= capacity of j
                for j in subAlternatives['id']:
                    [capacity_j] = grandAlternatives.loc[grandAlternatives['id']==j,'capacity']
                    LHS = [(1,W[j])]
                    model.addConstr(LinExpr(LHS)<=capacity_j, name='W<=capacity[%s]'%(j))
                
                #### W[j] <= sum_taz sum_destin Flow[taz,destin] * P[taz,destin,j]
                for j in subAlternatives['id']:
                    LHS = [(1,W[j])]
                    for taz in subIndividuals['TAZ']:
                        for destin in range(numDestins):
                            LHS += [(-Flow[taz,destin],P[taz,destin,j])]
                    model.addConstr(LinExpr(LHS) <= 0, name='W<=Flow*P[%s]'%(j))
                
                ### X <= X : Required
                for taz in subIndividuals['TAZ']:
                    for destin in range(numDestins):
                        for j in vanish[taz,destin]:
                            LHS = [(1,P[taz,destin,j])]
                            model.addConstr(LinExpr(LHS)==0, name = 'P[%s,%s,%s]=0'%(taz,destin,j))
                        for j in candidate[taz,destin]:
                            for k in candidate[taz,destin]:
                                if j != k:
                                    LHS = [(1,P[taz,destin,j]),(- pwa[taz,destin,j] / pwa[taz,destin,k], P[taz,destin,k]),(1,Y[k])]
                                    model.addConstr(LinExpr(LHS)<=1+pow(10,-tolError), name='Eq.X <= Z (%s,%s,%s,%s)'%(taz,destin,j,k))
                
                ## Set Objective
                objTerms = []
                for j in subAlternatives['id']:
                    objTerms += [(1,W[j])]
                model.setObjective(LinExpr(objTerms), GRB.MAXIMIZE)
                
                def mycallback(model, where):
                    if where == GRB.Callback.MIPSOL:
                        # make a list of edges selected in the solution
                        pjVal = {}
                        yVal = {}
                
                        SUM = {}
                        sumV = {}
                        for taz in subIndividuals['TAZ']:
                            for destin in range(numDestins):
                                SUM[taz,destin] = []
                                sumV[taz,destin] = 0.0
                                for j in subAlternatives['id']:
                                    pjVal[taz,destin,j] = model.cbGetSolution(P[taz,destin,j])
                                    SUM[taz,destin] += [(1,P[taz,destin,j])]
                                    sumV[taz,destin] += pjVal[taz,destin,j]
                                
                        sumOne = 0
                        theSelected = []
                        for j in subAlternatives['id']:
                            if model.cbGetSolution(Y[j]) > 1 - 0.0001:
                                yVal[j] = 1
                                sumOne += 1
                                theSelected += [j]
                            if model.cbGetSolution(Y[j]) < 0 + 0.0001:
                                yVal[j] = 0
                            if model.cbGetSolution(Y[j]) <= 1 - 0.0001 and model.cbGetSolution(Y[j]) >= 0 + 0.0001:
                                print('### wrong Y[%s] = %s'%(j,model.cbGetSolution(Y[j])))
                        if sumOne != numHubs:
                            print('### Wrong Subset')
                            
                        z_iYINT = {}
                        wHat = {}
                        wHatPrime = {}
                        zero_z = {}
                        for taz in subIndividuals['TAZ']:
                            for destin in range(numDestins):
                                z_iYINT[taz,destin] = 0.0
                                zero_z[taz,destin] = True
                                for j in theSelected:
                                    if j in candidate[taz,destin]:
                                        z_iYINT[taz,destin] += pwa[taz,destin,j]
                                        zero_z[taz,destin] = False
                                if zero_z[taz,destin] == False:
                                    wHat[taz,destin] = pow(z_iYINT[taz,destin],logSum) / (1 + pow(z_iYINT[taz,destin],logSum))
                                    wHatPrime[taz,destin] = logSum * pow(z_iYINT[taz,destin],logSum - 1) / pow(1 + pow(z_iYINT[taz,destin],logSum),2)
                                    
                        for taz in subIndividuals['TAZ']:
                            for destin in range(numDestins):
                                if zero_z[taz,destin] == False:
                                    if sumV[taz,destin] > wHat[taz,destin] + pow(10,-tolError):
                                        LHS = SUM[taz,destin] + []
                                        rhs = wHat[taz,destin] 
                                        for j in subAlternatives['id']:
                                            LHS += [(- wHatPrime[taz,destin] * pwa[taz,destin,j], Y[j])]
                                        for j in theSelected:
                                            rhs = rhs - wHatPrime[taz,destin] * pwa[taz,destin,j]                            
                                        model.cbLazy(LinExpr(LHS)<=rhs + pow(10,-tolError))
                        
                                    if sumV[taz,destin] < wHat[taz,destin] - pow(10,-tolError):
                                        LHS = SUM[taz,destin] + []
                                        rhs = wHat[taz,destin] 
                                        for j in subAlternatives['id']:
                                            if yVal[j] == 1:
                                                LHS += [(-1,Y[j])]
                                                rhs = rhs - 1
                                            if yVal[j] == 0:
                                                LHS += [(+1,Y[j])]
                                        model.cbLazy(LinExpr(LHS)>=rhs - pow(10,-tolError))
                
                # Warm Start
                numCores = 128 # number of cores that were used for the incumbent
                if warmStart == True:
                    incumbent = pd.read_excel('../arr_parallel/result/summary/result_constrainedNL_pnr_origin%s_I%s_J%s_p%s_summary_lambda(%s)_numCores%s.xlsx'%(numOrigins,numOrigins*numDestins,numAlternatives,numHubs,int(logSum*100),numCores))
                    notSelected = copy.deepcopy(list(subAlternatives['id']))
                    theSelected = []
                    for j in range(numHubs):
                        [hub_j] = incumbent.loc[incumbent['Instance']==instance,'selectedHub%s'%j]
                        notSelected.remove(hub_j)
                        Y[hub_j].start = 1
                        theSelected += [hub_j]
    
                    for not_j in notSelected:
                        Y[not_j].start = 0
                    
                    totalPW = {}
                    for taz in subIndividuals['TAZ']:
                        for destin in range(numDestins):
                            totalPW[taz,destin] = 0.0
                            for j in theSelected:
                                totalPW[taz,destin] += pwa[taz,destin,j] 
                    
                    for taz in subIndividuals['TAZ']:
                        for destin in range(numDestins):
                            for j in theSelected:
                                if totalPW[taz,destin] > 0.0 + pow(10, -tolError):
                                    prob_ij = pow(totalPW[taz,destin],logSum) / (1 + pow(totalPW[taz,destin],logSum)) * pwa[taz,destin,j] / totalPW[taz,destin]
                                    P[taz,destin,j].start = prob_ij
                            for j in notSelected:
                                P[taz,destin,j].start = 0.0
    
    
                # update and solve the model
                model.update()
                #model = model.relax()
                model.Params.lazyConstraints = 1
                model.optimize(mycallback)
                
                
                # post matter records opt solution if no time limit
                if timeLimit == False:
                    variableName = []
                    variableValue = []
                    for v in model.getVars():
                        variableName += [v.varname]
                        variableValue += [v.x]
                    
                    optSolution = pd.DataFrame(list(zip(variableName, variableValue)),columns =['varName', 'varVal'])
                    optSolution.to_csv(r'result/origin%s/opt_constrainedNL_warm%s_logSum%s_pnr_origin%s_I%s_J%s_p%s_inst%s.csv'%(numOrigins,warmStart,int(logSum*100),numOrigins,numOrigins*numDestins,numAlternatives,numHubs,instance), index = False)#Check
                    
                    
                    theSelected = []            
                    for j in subAlternatives['id']:
                        [Y_j] = optSolution.loc[optSolution['varName']=='Y[%s]'%(j),'varVal']
                        if Y_j > 1 - 0.0001:
                            theSelected += [j]            
                    
                    # demand(theSelected)
                    totalPW = {}
                    for taz in subIndividuals['TAZ']:
                        for destin in range(numDestins):
                            totalPW[taz,destin] = 0.0
                            for j in theSelected:
                                totalPW[taz,destin] += pow(pw[taz,destin,j] / pw[taz,destin,0], 1/logSum)
                    
                    unconstrainedVal = 0.0 
                    totalDemand = 0.0
                    underCapacity = 0
                    overCapacity = 0
                    for j in theSelected:
                        demand_j = 0.0
                        for taz in subIndividuals['TAZ']:
                            for destin in range(numDestins):
                                demand_j += Flow[taz,destin] * pow(totalPW[taz,destin],logSum) / (1 + pow(totalPW[taz,destin],logSum)) * pow(pw[taz,destin,j]/pw[taz,destin,0],1/logSum) / totalPW[taz,destin]
                        [capacity_j] = grandAlternatives.loc[grandAlternatives['id']==j,'capacity']
                        totalDemand += min(demand_j,capacity_j)
                        unconstrainedVal += demand_j
                        if demand_j > capacity_j:
                            overCapacity += 1
                            print(j, demand_j, capacity_j, 'over capacity', capacity_j)
                        else:
                            underCapacity += 1
                            print(j, demand_j, capacity_j, 'under capacity', demand_j)
                        
                    print('ILP OPT Val=',model.objVal)
                    print('accurate=',totalDemand)
                    print('underCapacity=',underCapacity)
                    print('overCapacity=',overCapacity)
                    print('### END')
                
                    machineArray += [machineName]
                    warmArray += [warmStart]
                    logSumArray += [logSum]
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
                    countArray += [int(model.NodeCount)]
                    
                    ilpTable = pd.DataFrame(list(zip(machineArray,warmArray,logSumArray,originArray,iArray,jArray,pArray,instanceArray,ilpObjArray,accurateArray,unconstrainedArray,underArray,overArray,runArray,countArray)),columns =['Machine','Warm Start','logSum','Origins','I','J','p','instance','ILP OPT','Accuarate','ifUnconstrained','underCapacity','overCapacity','runTime','NodeCount'])
                    ilpTable.to_csv(r'result/MILP_constrainedNL_warm%s_logSum%s_pnr_origin%s_I%s_J%s_p%s.csv'%(warmStart,int(logSum*100),numOrigins,numOrigins*numDestins,numAlternatives,numHubs), index = False)#Check
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    
                    
