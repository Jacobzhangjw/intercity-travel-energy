def sdf_for_replace(dff, breaks=[0, 500, 1000, 1500, 2000, 5000], conditions_loc=[0], dis='distance_eu'):
    # this func is for seperating data into flow to be adjusted and flows to be remained
    
    df = dff.copy(deep=True)

    # labeling distance
    bins = pd.IntervalIndex.from_breaks(breaks)
    labels = bins.astype(str)
    df['dislevels'] = pd.cut(df[dis], bins, labels)

    # filter sdf by conditions
    cats=bins[conditions_loc]
    sdf = df[df['dislevels'].isin(cats)].copy(deep=True)
    sdf_left = df[~df['dislevels'].isin(cats)].copy(deep=True)
    print('flows shifted in ranges:', cats)
    
    return (sdf, sdf_left)
	
def replace_flows(sdf, fromcol=['train'], tocol=['flight'], additional_weights = {'car': 1, 'train': 1, 'flight': 1}):
    
    '''    
    support 1 to 1, 1 to 2, and 2 to 1 flow shifting
    '''

    # this func shift flows of df, controlled by from and to cols and weights

    flowcol = ['car', 'train', 'flight']   
    flows = sdf.copy(deep=True)

    # initial values
    totalf = flows[flowcol].sum(1)
    ini_weights = flows[flowcol].divide(totalf, axis=0)

    # calculating
    adjust_weights = pd.DataFrame(columns=flowcol)

    if (len(fromcol)==1) & (len(tocol)==1):
        left_mode = [c for c in flowcol if c not in [fromcol[0],tocol[0]]][0]
        # preserve original flow for the exclusive mode
        adjust_weights[left_mode] = ini_weights[left_mode]
        # update tocol
        adjust_weights[tocol[0]] = (ini_weights[tocol[0]]) + (ini_weights[fromcol[0]] * additional_weights[fromcol[0]])
        # update what's left of fromcol
        adjust_weights[fromcol[0]] = ini_weights[fromcol[0]] * (1 - additional_weights[fromcol[0]])
    elif (len(fromcol)==2) & (len(tocol)==1):
        adjust_weights[tocol[0]] = ini_weights[tocol[0]]
        for m in fromcol:
            # update tocol
            adjust_weights[tocol[0]] = adjust_weights[tocol[0]] + ini_weights[m] * additional_weights[m]
            # updat what's left of fromcol
            adjust_weights[m] = ini_weights[m] * (1 - additional_weights[m])
    elif (len(fromcol)==1) & (len(tocol)==2):
        for m in tocol:
            # update tocl 
            adjust_weights[m] = ini_weights[m] + ini_weights[fromcol[0]] * additional_weights[fromcol[0]] * additional_weights[m]
        # update what's left of fromcol
        adjust_weights[fromcol[0]] = ini_weights[fromcol[0]] * (1 - additional_weights[fromcol[0]])

    adjust_flows = adjust_weights.multiply(totalf, axis=0)

    return adjust_flows
    
def calculate_trip_energy(od, flow_cols=['car','train','flight'], ecf_dict={'car':1.25, 'train':0.28, 'flight':1.07}, durations=False):
    # flow_cols unit: number of passengers
    # distance unit: meter
    
    df = od.copy(deep=True)
    
    for m in flow_cols:
        df[m+'_e'] = df[m] * (df[m+'_distance']) * ecf_dict[m] / 10**6
        
    if durations:
        for m in flow_cols:
            df['timecost_'+m] = df[m+'_duration'] * df[m]
    else:
        pass
    
    df.reset_index(drop=True, inplace=True)
    
    return df
    
# pipline using this func
# subset a df based on some conditions: sdf
sdf = df[df['dislevels'].isin(cats)].copy(deep=True)
sdf_left = df[~df['dislevels'].isin(cats)].copy(deep=True)

# replace flows
flows = replace_flows(sdf, fromcol=['train'], tocol=['flight'], additional_weights = {'car': 1, 'train': 1, 'flight': 1})

# update energy
sdf[flowcol] = flows
sdf = calculate_trip_energy(sdf)
sdf.set_index(pd.to_datetime(sdf['date'], format='%Y%m%d'), inplace=True)
df = pd.concat([sdf, sdf_left])
