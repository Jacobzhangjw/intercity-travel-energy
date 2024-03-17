import pandas as pd
import numpy as np
import os
import geopandas as gpd
from shapely.geometry import Point, LineString
from geopy.distance import geodesic as GD
from scipy.stats import linregress
import jenkspy
from sklearn.preprocessing import MinMaxScaler
from pathlib import Path
import datetime
from itertools import permutations, combinations, product
from sklearn.metrics import pairwise_distances
import matplotlib.pyplot as plt
import matplotlib.ticker as mticker
import matplotlib.lines as mlines
import matplotlib.patches as mpatches
import seaborn as sns

pd.set_option('display.max_columns', None)

# for unifying od city names from map service provider
def cityname_Amap(acity, printResult=False):
    
    time.sleep(random.randint(1,3))
    geocoding_url = "https://restapi.amap.com/v3/geocode/geo"
    paras = {'key':'',
             'address': '北京市'
            }
    paras['address'] = acity
    
    try:
        response = requests.get(geocoding_url, params=paras, timeout=8)
        result = response.json()
        response.close()
    except requests.exceptions.RequestException as e:
        print(acity, e)
        df = pd.DataFrame(dict(zip(['full','province','level','adcode','location'], np.repeat(np.nan, 5))), index=[0])
        df['requestid'] = acity
        return df
    if printResult:
        print(result)
    if result['info'] != 'OK':
        print(acity, 'failed to search from API')
        df = pd.DataFrame(dict(zip(['full','province','level','adcode','location'], np.repeat(np.nan, 5))), index=[0])
        df['requestid'] = acity
        return df
    else:
        df = pd.DataFrame(result['geocodes'])[['formatted_address','province','level','adcode','location']]
        df['requestid'] = acity
        df.rename({'formatted_address':'full'}, axis=1, inplace=True)
        return df

apinames = []
for i in tqdm(cities['names'].tolist()):
    result = cityname_Amap(i)
    c = 0
    while result.dropna().shape[0]==0:
        result = cityname_Amap(i)
        c+=1
        if c == 3:
            break
    apinames.append(result)
df = pd.concat(apinames)

# for unifying OD order and cleaning repeated flows
def clean_od(p, city2id):
    df = pd.read_csv(p).iloc[:,1:-1]
    df.columns = ['ID','O','D','date','direct','amount','car','train','flight']
    df.dropna(inplace=True)
    df.drop_duplicates(inplace=True)
    for c in ['O','D','date','direct']:
        df[c] = df[c].astype(str)
        df[c] = df[c].str.strip()
    df['OID'] = df['O'].map(city2id)
    df['DID'] = df['D'].map(city2id)
    df = df[(df.OID!=999)&(df.DID!=999)] # align with shp data
    for c in ['amount','car','train','flight']:
        df[c] = df[c].astype(float)
    df.dropna(inplace=True)
    df.drop_duplicates(['OID','DID','date','amount'], inplace=True)
    
    # reverse direction of 迁入
    temp = df[df.direct=='迁入'].copy(deep=True)
    temp[['O','D']] = temp[['O','D']].rename(columns={'O': 'D', 'D': 'O'})[['O','D']]
    temp[['OID','DID']] = temp[['OID','DID']].rename(columns={'OID': 'DID', 'DID': 'OID'})[['OID','DID']]
    df[df.direct=='迁入'] = temp
    df.drop(columns=['direct','ID'], axis=1, inplace=True)
    df.dropna(inplace=True)
    df.drop_duplicates(['OID','DID','date'], inplace=True)
    return df

cities = pd.read_excel(root / 'Inter' / 'cities_v4_all.xlsx')
city2id = dict(zip(cities.tc.str.strip(), cities.cindex))

ods = []
for p in tqdm(paths):
    od = clean_od(p, city2id)
    ods.append(od)
od = pd.concat(ods)
od.dropna(inplace=True)
od.drop_duplicates(['OID','DID','date'], inplace=True)
od = od[['OID','DID'] + od.columns[:-2].tolist()]
df = od.reset_index(drop=True)
df.reset_index(drop=True).to_feather(root / 'Inter' / 'flows.feather')