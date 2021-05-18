# %%
import json
import requests
import pandas as pd
import altair as alt
from vega_datasets import data as v_data

class Data:
    def __init__(self, data=None):
        self.data = data

def geoshapes():
    '''import US state and county geoshape data'''
    data = Data()
    data.counties = alt.topo_feature(v_data.us_10m.url, 'counties')
    data.states = alt.topo_feature(v_data.us_10m.url, 'states')
    return data

def texas():
    '''import texas county-level vaccination data'''
    return pd.read_excel(
        'https://dshs.texas.gov/immunize/covid19/COVID-19-Vaccine-Data-by-County.xls',
        sheet_name=1, engine='openpyxl'
    ).dropna(
        axis=1, how='all'
    ).dropna(
        axis=0, how='all'
    )[3:].rename(columns={'County Name': 'county'})

def counties():
    '''import US county-level vaccination data + merge with TX data'''
    resp = requests.get('https://covid.cdc.gov/covid-data-tracker/COVIDData/getAjaxData?id=vaccination_county_condensed_data')
    raw = json.loads(resp.text)
    counties = pd.DataFrame(raw['vaccination_county_condensed_data']).fillna(-1)
    counties.columns = counties.columns.str.lower()
    counties['pct'] = counties['series_complete_pop_pct']
    counties['label'] = counties['county'] + ' County, ' + counties['stateabbr']
    counties['sfips'] = pd.to_numeric(counties['fips'].str[:2], errors='coerce')
    counties['fips'] = pd.to_numeric(counties['fips'], errors='coerce')
    tx = texas()
    pops = ['Population\n12+', 'Population, 16+', 'Population, 65+']
    tx['population'] = tx[pops].sum(axis=1)
    tx = tx[tx['population'] > 0]
    tx['pct+1'] = (tx['Vaccine Doses Administered'] / tx['population'] * 100 + 1).astype(float).round(decimals=1)
    tx = tx[['county', 'pct+1']]
    counties = counties.merge(tx, on='county', how='left')
    counties['pct+1'] = counties['pct+1'].fillna(0)
    counties['pct'] = counties['pct'] + counties['pct+1']
    return counties

def state_map(counties):
    '''get state FIPS mappings from all counties in county dataset'''
    return counties[['statename', 'sfips']].drop_duplicates().dropna()

def states(state_map):
    '''get state vaccination data'''
    data = Data()
    states = pd.read_csv('https://github.com/owid/covid-19-data/blob/master/public/data/vaccinations/us_state_vaccinations.csv?raw=true').fillna(method='ffill')
    states['dt'] = pd.to_datetime(states['date'])
    states = states[states['dt'] > '01/08/2021']
    states['pct'] = states['people_vaccinated_per_hundred']
    states['week'] = states['dt'].dt.isocalendar().week
    states.location = states.location.str.replace('New York State', 'New York')
    states = states.merge(state_map, left_on='location', right_on='statename', how='left').dropna()
    data.long = states.groupby(['week', 'location']).max().reset_index()
    states = states.pivot_table(index=['sfips', 'statename'], columns='week', values='pct', aggfunc='max')
    data.min_week, data.max_week = states.columns.min(), states.columns.max()
    states.columns = states.columns.astype(str)
    data.columns = states.columns.to_list()
    data.wide = states.reset_index()
    return data

def demographics():
    '''get demographic trends'''
    resp = requests.get('https://covid.cdc.gov/covid-data-tracker/COVIDData/getAjaxData?id=vaccination_demographic_trends_data')
    raw = json.loads(resp.text)
    demos = pd.DataFrame(raw['vaccination_demographic_trends_data'])
    demos.columns = demos.columns.str.lower()
    demos = demos.rename(columns={'demographic_category': 'group', 'administered_dose1_pct_agegroup': 'pct'}).set_index('date')[['group', 'pct']]
    demos['group'] = demos['group'].str.lower()
    demos = demos[~demos.group.str.contains('known')].reset_index()
    demos.columns = demos.columns.str.lower()
    sex = demos[demos.group.str.contains('sex')]
    eth = demos[demos.group.str.contains('eth')]
    sex.group = sex.group.str.split('_').str[-1]
    eth.group = eth.group.str.split('_').str[-1].str.replace('aian', 'asian')
    sex['dt'] = pd.to_datetime(sex.date)
    sex = sex[sex['dt'] > '01/08/2021']
    sex['week'] = sex['dt'].dt.isocalendar().week
    eth['dt'] = pd.to_datetime(eth.date)
    eth = eth[eth['dt'] > '01/08/2021']
    eth['week'] = eth['dt'].dt.isocalendar().week
    data = Data()
    data.sex, data.eth = sex, eth
    return data

def hesitancy(state_map, local=False):
    '''get county and state level hesitancy data, split into county and state set'''
    if local:
        src = 'hesitancy.csv'
    else:
        src = 'https://data.cdc.gov/api/views/q9mh-h2tw/rows.csv'
    relevant = ['FIPS Code', 'County Name', 'State', 'Estimated hesitant', 'Estimated hesitant or unsure', 'Estimated strongly hesitant']
    hes = pd.read_csv(src, usecols=relevant).rename(columns={'County Name': 'county', 'FIPS Code': 'fips', 'State': 'statename'})
    hes.columns = hes.columns.str.lower()
    hes['pct'] = (hes[hes.columns[hes.columns.str.contains('hesitant')]].sum(axis=1) * 100).round(decimals=1)
    hes['statename'] = hes['statename'].str.title()
    hes_county = hes[['fips', 'county', 'statename', 'pct']]
    hes_states = hes_county.merge(state_map, on='statename', how='left').dropna()
    hes_states = hes_states.groupby(['statename', 'sfips']).mean()['pct'].reset_index()
    data = Data()
    data.county, data.states = hes_county, hes_states
    return data