# -*- coding: utf-8 -*-
"""
Created on Mon Nov  4 10:14:14 2019
@author: ga47jes
"""

import pandas as pd
import statistics


def calc_flex_bat(my_ems):
    nsteps = my_ems['time_data']['nsteps']
    ntsteps = my_ems['time_data']['ntsteps']
    Bat_flex = pd.DataFrame(0, index=range(nsteps), columns=range(7))
    Bat_flex.columns = ['Sch_P', 'Neg_P', 'Pos_P', 'Neg_E', 'Pos_E', 'Neg_Pr', 'Pos_Pr']
    dat1 = {'col1': my_ems['optplan']['bat_grid2bat'], 
            'col2': my_ems['optplan']['bat_input_power'],
            'col3': my_ems['optplan']['bat_output_power'],
            'col4': my_ems['optplan']['bat_SOC']}
    dat1 = pd.DataFrame(data=dat1)
    # Bat_flex.iloc[:, 0] = my_ems['optplan']['bat_grid2bat']
    Bat_maxP = my_ems['devices']['bat']['maxpow']
    Bat_minP = my_ems['devices']['bat']['minpow']
    Bat_maxE = my_ems['devices']['bat']['stocap']
    Bat_minE = 0.500

    # Battery negative flexibility
    for i in range(nsteps):
        Bat_flex.iloc[i, 0] = dat1.iloc[i, 2]  - dat1.iloc[i, 1]
        nflex_P = Bat_maxP-dat1.iloc[i, 1]+dat1.iloc[i, 2]
        if (dat1.iloc[i, 3]*Bat_maxE/100 < Bat_maxE) and (nflex_P > 0):
            req_steps = int(round(ntsteps*(Bat_maxE-dat1.iloc[i, 3]*Bat_maxE/100)/nflex_P))
            if nflex_P < Bat_minP:
                req_steps = 0
            elif (req_steps != 0) and (req_steps + i <= nsteps-1): 
                req_steps = req_steps + i
            elif req_steps != 0:
                req_steps = nsteps - 1
    
            if req_steps > 0:                                
                j = i
                while (j < nsteps) and (j < req_steps) and \
                        nflex_P <= (Bat_maxP-dat1.iloc[j, 1]+dat1.iloc[j, 2]):
                    j = j+1
                Bat_flex.iloc[i, 1] = -1*nflex_P
                Bat_flex.iloc[i, 3] = Bat_flex.iloc[i, 1]*(j-i)/ntsteps
    
            # Usable energy
                cbat_E = 0
                for k in range(j, nsteps):
                    cbat_E = cbat_E + (dat1.iloc[k, 1])/ntsteps  
                
            # Computing the exact flexibility
                neg_Eflex = Bat_flex.iloc[i, 3]
                while (cbat_E < abs(neg_Eflex)) and (j >= i):
                    neg_Eflex = neg_Eflex + abs(Bat_flex.iloc[i, 1]/ntsteps)
    #                cbat_E = cbat_E + (dat1.iloc[j-1, 1]/4)
                    j = j-1
                    Bat_flex.iloc[i, 3] = Bat_flex.iloc[i, 1]*(j-i)/ntsteps
                if j <= i:
                    Bat_flex.iloc[i, 1] = 0
                    Bat_flex.iloc[i, 3] = 0                                     
                    
    # Pricing
    for i in range(nsteps):
        if Bat_flex.iloc[i, 1] < 0 and i < nsteps-1:
            req_steps = int(round(Bat_flex.iloc[i, 3]*ntsteps/Bat_flex.iloc[i, 1]))
            bch_index = [k+i+req_steps for k, l in enumerate(my_ems['optplan']['bat_input_power'][i+req_steps:nsteps]) if l > 0]
            pow_ch = []
            price_ch = []
            for k in range(0, len(bch_index)):
                pow_ch.append(my_ems['optplan']['bat_input_power'][bch_index[k]])
                price_ch.append(my_ems['fcst']['ele_price_in'][bch_index[k]])            
            bat_ch = pd.DataFrame({'slots':bch_index, 'Bat_in':pow_ch, 'price':price_ch})
            bat_ch = bat_ch.sort_values(by=['price'], ascending=False)    
            e_bal = abs(Bat_flex.iloc[i, 3])
            e_prc = 0
            for k in range(0, len(bch_index)):
                if e_bal - bat_ch.iloc[k,1]/ntsteps >= 0:
                    e_bal = e_bal - bat_ch.iloc[k,1]/ntsteps
                    e_prc = e_prc + bat_ch.iloc[k,2]*bat_ch.iloc[k,1]/ntsteps                    
                elif (e_bal - bat_ch.iloc[k,1]/ntsteps < 0) and (e_bal > 0):
                    e_prc = e_prc + bat_ch.iloc[k,2]*e_bal
                    e_bal = 0
            Bat_flex.iloc[i, 5] = e_prc/Bat_flex.iloc[i, 3]
        elif Bat_flex.iloc[i, 1] < 0 and i == nsteps-1:
            Bat_flex.iloc[i, 5] = -1*my_ems['fcst']['ele_price_in'][i]

# PV_Bat_Integration
    # Battery positive flexibility
    # Feeding into the grid
    for i in range(nsteps):
        ava_ebatout = dat1.iloc[i, 3]*Bat_maxE/100 - Bat_minE
        if ava_ebatout > 0:
            pflex_P = Bat_maxP - dat1.iloc[i, 0] + dat1.iloc[i, 1] - dat1.iloc[i, 2]
            if pflex_P > 0:
                ava_steps = int(round(ntsteps*ava_ebatout/pflex_P))
                if (Bat_maxP - dat1.iloc[i, 2]) < Bat_minP:
                    ava_steps = 0
                elif (ava_steps != 0) and (ava_steps + i <= nsteps-1):
                    ava_steps = ava_steps + i
                elif ava_steps != 0:
                    ava_steps = nsteps-1  
            
            if ava_steps > 0:
                j = i
                while (j < nsteps) and (j < ava_steps) and  \
                        pflex_P <= (Bat_maxP-dat1.iloc[j, 2]):
                    # Add minimum pos flex power in the previous line
                    j = j+1
                Bat_flex.iloc[i, 2] = (Bat_maxP-dat1.iloc[i, 2])
                Bat_flex.iloc[i, 4] = Bat_flex.iloc[i, 2]*(j-i)/ntsteps    
                
                
                # Rechargable energy
                cbat_E = 0
                for k in range(j,nsteps):
                    cbat_E = cbat_E + (Bat_maxP-dat1.iloc[k, 1])/ntsteps       
                
                # Computing the exact flexibility
                pos_Eflex = Bat_flex.iloc[i, 4] 
                while (cbat_E < pos_Eflex) and (j >= i):
                    pos_Eflex = pos_Eflex - Bat_flex.iloc[i, 2]/ntsteps
                    cbat_E = cbat_E + (Bat_maxP-dat1.iloc[j-1, 1])/ntsteps
                    j = j-1
                    Bat_flex.iloc[i, 4] = Bat_flex.iloc[i, 2]*(j-i)/ntsteps
                if j <= i:
                    Bat_flex.iloc[i, 2] = 0
                    Bat_flex.iloc[i, 4] = 0
            
    # Curtailing scheduled charging
    for i in range(nsteps):
         if dat1.iloc[i, 0] > Bat_minP:
             feed_steps = int(round(Bat_flex.iloc[i, 4]*ntsteps/Bat_flex.iloc[i, 2]))
             j = i
             while (j < nsteps) and (dat1.iloc[i, 0] <= dat1.iloc[j, 0]):
                 j = j+1
             pflex_P = dat1.iloc[i, 0]
             charg_steps = j-i    
             act_steps = min(feed_steps, charg_steps)
             Bat_flex.iloc[i, 2] = Bat_flex.iloc[i, 2] + pflex_P
             Bat_flex.iloc[i, 4] = Bat_flex.iloc[i, 2]*act_steps/ntsteps  
             
    # Pricing 
    # for i in range(1):
    #     if Bat_flex.iloc[i, 2] > 0 and i < nsteps-1:
    #         req_steps = int(round(Bat_flex.iloc[i, 4]*ntsteps/Bat_flex.iloc[i, 2]))
    #         req_energy = Bat_flex.iloc[i, 4]
    #         bdh_index = [k+i+req_steps for k, l in enumerate(my_ems['optplan']['bat_output_power'][i+req_steps:nsteps]) if l > 0],
    #         soc_act = []
    #         soc_act[:] = [x*Bat_maxE/100 for x in my_ems['optplan']['bat_SOC']]              
    #         for k in range(i+req_steps, nsteps):
    #             soc_act[k] = soc_act[k] - Bat_flex.iloc[i, 2]/ntsteps                 
    #         # fnd_socmin = [k for k, x in enumerate(soc_act) if x < 0.13]
    #         # fnd_socmin = fnd_socmin[0]
    #         pow_dh = []
    #         steps_exp = []
    #         price_exp = []
    #         power_exp = []
    #         steps_imp = []
    #         power_imp = []
    #         price_imp = []
    #         for k in range(i+req_steps, nsteps):
    #             if my_ems['optplan']['grid_export'][k] > 0:
    #                 steps_exp.append(k) 
    #                 price_exp.append(my_ems['fcst']['ele_price_out'][k]) 
    #                 if (Bat_maxP - dat1.iloc[k,1] > my_ems['optplan']['grid_export'][k]):
    #                     power_exp.append(Bat_maxP - my_ems['optplan']['grid_export'][k] - dat1.iloc[k,1])
    #                 else:
    #                     power_exp.append(Bat_maxP - dat1.iloc[k,1])                    
    #             # Import to charge
    #             price_imp.append(my_ems['fcst']['ele_price_in'][k])
    #             power_imp.append(Bat_maxP - dat1.iloc[k,1])
    #             steps_imp.append(k)
    #         frame_exp = pd.DataFrame({'slots':steps_exp, 'power':power_exp, 'price':price_exp})
    #         frame_exp = frame_exp.sort_values(by = ['price'])
    #         frame_exp = frame_exp[frame_exp.power != 0]
    #         frame_imp = pd.DataFrame({'slots':steps_imp, 'power':power_imp, 'price':price_imp})
    #         frame_imp = frame_imp.sort_values(by = ['price'])
    #         frame_imp = frame_imp[frame_imp.power != 0]
    #         print(frame_imp)
    #         if(frame_exp.empty == False):                
    #             for k in range(0, len(frame_exp.index)):
    #                 if req_energy > 0:
    #                     req_energy = req_energy - frame_exp.power[k]/ntsteps
    #     elif Bat_flex.iloc[i, 2] > 0 and i == nsteps-1:
    #         Bat_flex.iloc[i, 6] = -1*my_ems['fcst']['ele_price_in'][i]         
            
    for i in range(nsteps):
        if Bat_flex.iloc[i, 2] > 0 and i < nsteps-1:
            min_val = my_ems['fcst']['ele_price_in']
            min_val = statistics.mean(min_val[i:nsteps])
            Bat_flex.iloc[i, 6] = 1*min_val        
        elif Bat_flex.iloc[i, 2] > 0 and i == nsteps-1:
            Bat_flex.iloc[i, 6] = my_ems['fcst']['ele_price_in'][i]
             
    return Bat_flex
