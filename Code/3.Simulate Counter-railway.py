# train to car in 200-400 km
# train to flight in 400-1000 km

# modal shifting weights from 0.2 to 1
for w in np.arange(0,1.2,0.2).round(1)[1:]:
    train_weight = w
    df = flows.copy(deep=True) 
   
    for m in flowcol:
        df[m+'_distance'] = df[m+'_distance'] / 1000 # to km
        df[m+'_duration'] = df[m+'_duration'] / 3600 # to hour

    df['disavr'] = df[discol].mean(1)
    
    print(df.shape)
    
    sdf, sdf_left = sdf_for_replace(df, breaks=[0, 200, 400, 1000, 4000], conditions_loc=[1], dis='disavr')
    sdf[flowcol] = replace_flows(sdf, fromcol=['train'], tocol=['car'], additional_weights = {'car': 1, 'train': train_weight, 'flight': 1})
    sdf = calculate_trip_energy(sdf)
    df1 = pd.concat([sdf_left, sdf])
    print(df1.shape)
    
    sdf, sdf_left = sdf_for_replace(df1, breaks=[0, 200, 400, 1000, 4000], conditions_loc=[2], dis='disavr')
    sdf[flowcol] = replace_flows(sdf, fromcol=['train'], tocol=['flight'], additional_weights = {'car': 1, 'train': train_weight, 'flight': 1})
    sdf = calculate_trip_energy(sdf)
    df2 = pd.concat([sdf_left, sdf])
    
    print(df2.shape)
    
    df2.reset_index(drop=True).drop('dislevels', axis=1).to_feather(root / 'Final' / 'ReplaceFlows' / ('flowsE_fromtrain' + str(train_weight) + '.feather'))