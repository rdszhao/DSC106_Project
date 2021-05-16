# %%
import numpy as np
import pandas as pd
import altair as alt
import json
import requests
from urllib.request import urlopen
# %%
import plotly.express as px
import plotly.graph_objs as go
# %%
counties_mapping = 'https://raw.githubusercontent.com/plotly/datasets/master/geojson-counties-fips.json'
with urlopen(counties_mapping) as resp:
    c_mapping = json.load(resp)
# %%
counties_src = 'https://covid.cdc.gov/covid-data-tracker/COVIDData/getAjaxData?id=vaccination_county_condensed_data'
resp = requests.get(counties_src)
data = json.loads(resp.text)
counties = pd.DataFrame(data['vaccination_county_condensed_data']).dropna()
counties.columns = counties.columns.str.lower()
counties['pct'] = counties['series_complete_pop_pct']
counties['label'] = counties['county'] + ' County, ' + counties['stateabbr']
state_map = counties[['statename', 'stateabbr']].drop_duplicates()
counties = counties[['fips', 'label', 'pct']]
# %%
fig = px.choropleth(
    counties, geojson=c_mapping,
    locations='fips', color='pct', color_continuous_scale='haline',
    range_color=(0, 100), scope='usa', labels={'pct': 'percentage vaccinated'},
    hover_data=['label']
)
fig.show()
# %%
states = pd.read_csv('data/owid_vaccinations.csv')
# states['date'] = pd.to_datetime(states['date'])
states = states.fillna(method='ffill')
states['pct'] = states['people_vaccinated_per_hundred']
states = states.merge(state_map, left_on='location', right_on='statename', how='left')
states['state'] = states['stateabbr'].str.strip()
# %%
fig = px.choropleth(
    states,
    locations='state', color='pct',
    locationmode='USA-states', scope='usa',
    range_color=(0, 100), color_continuous_scale='haline',
    labels={'pct': 'percentage vaccinated'},
    animation_frame='date'
)
fig.show()