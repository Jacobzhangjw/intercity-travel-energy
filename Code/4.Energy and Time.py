def add_levels(dff, breaks=[0, 0.5, 1, 2, 5, 10, 30], col='popd'):
    df = dff.copy(deep=True)
    bins = pd.IntervalIndex.from_breaks(np.array(breaks))
    labels = bins.astype(str)
    df['levels'] = pd.cut(df[col], bins, labels)
    return df
    
# for obatining OD energy and time
def od_et_agg(flows, cities, explabel):
    flowcol = ['car', 'train', 'flight']
    discol = ['car_distance', 'train_distance', 'flight_distance']
    durcol = ['car_duration', 'train_duration', 'flight_duration']
    timecol = ['car_t', 'train_t', 'flight_t']
    ecol = ['car_e', 'train_e', 'flight_e']

    # km, h, Mj MN
    dff = flows.copy(deep=True)

    # merge multi-modal duration to ODt, weighted by modal traffic
    for m in flowcol:
        dff[m+'_t'] = dff[m] * dff[m+'_duration']
    dff['t'] = dff[timecol].sum(1) / dff['amount']
    
    # MN person, Mj MN, hour
    df = dff.groupby(['OID','DID'])[['amount', *flowcol] + ecol].sum().reset_index()
    df[ecol] = df[ecol] * 2.388 * 10**-5 # MN Mj to MN TOE
    df['eod'] = df[ecol].sum(1)
    df['tod'] = dff.groupby(['OID','DID'])['t'].mean().reset_index()['t']
    
    for c in ['popu','poph'][:1]:
        df[c] = df.DID.map(dict(zip(cities.cindex, cities[c])))
    df['popu'] = df['popu'] * 10**-1 # MN person
    df['eod'] = df['eod'] # MN mj
    df[['amount', *flowcol]] = df[['amount', *flowcol]] * 10**-6 # MN person
    df['exp'] = explabel
    return df

# agg e and t
dfs = []
for p in paths:
    label = p.stem.split('_')[-1]
    df = od_et_agg(pd.read_feather(p), cities, label)
    print(label, df.shape)
    dfs.append(df)
dfs.append(od_et_agg(baseflows, cities, 'baseline'))
df = pd.concat(dfs)
df.reset_index(drop=True).to_feather(root / 'Final' / 'ReplaceFlows' / 'ode_all.feather')

# E,T gap, and ET ratio of cities
df = pd.read_feather(root / 'Final' / 'ReplaceFlows' / 'ode_all.feather')
data = df[df.exp.isin(['baseline','fromtrain1.0'])].copy(deep=True)
data['exp'] = data.exp.str.replace('fromtrain1.0','simu').tolist()

# destination energy (sum) and time (weighted by traffic)
time = data.groupby(['exp','DID']).apply(lambda data: (data[flowcol].sum(1).multiply(data['tod'], 1) / data[flowcol].sum().sum()).sum()).reset_index(name='td')
e = data.groupby(['exp','DID'])['eod'].sum().reset_index(name='ed')
data = time.merge(e)

# add city attributes
data = data.pivot(index=['DID'], columns='exp', values=['td','ed']).reset_index()
for c in ['name','popu','geochina','levels']:
    data[c] = data['DID'].map(dict(zip(cities.cindex, cities[c])))
data['popu'] = data['popu'] / 1000
data['geoid'] = data.geochina.map(dict(zip(['East China', 'Southwest China', 'South China', 'North China', 'Central China','Northwest China','Northeast China'],[1,2,3,4,5,6,7])))
data['levelsid'] = data['levels'].map(dict(zip(['medium & small cities','large cities','very large cities','megacity'][::-1], np.arange(4) + 1)))	
data.sort_values(['geoid','levelsid'], ascending=[True, True], inplace=True)

# e gap, t gap
data['egap'] = -(data['ed']['baseline'] - data['ed']['simu']) # Mtoe
data['tgap'] = (data['td']['baseline'] - data['td']['simu']) # hour
data['egapper'] = data['egap'] / data['popu'] 

# et ratio
data['et'] = data['egap'] / (data['tgap'])
data['etper'] = data['egapper'] / (data['tgap'])
data = data.reset_index(drop=True).set_index('DID')
data['geotiers'] = data['geochina'] + '-' + data['levels']
data = data.iloc[:,4:].droplevel(1, 1) # only keep gap columns