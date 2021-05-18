
"""
Created on Mon May 17 13:29:38 2021
@author: Shweta Kumar and Ray Zhao
"""

import streamlit as st
import pandas as pd
import altair as alt
import json
import requests
from vega_datasets import data


st.cache(persist=True)

#State Data
us_counties = alt.topo_feature(data.us_10m.url, 'counties')
counties_src = 'https://covid.cdc.gov/covid-data-tracker/COVIDData/getAjaxData?id=vaccination_county_condensed_data'
resp = requests.get(counties_src)
raw = json.loads(resp.text)
counties = pd.DataFrame(raw['vaccination_county_condensed_data']).fillna(-1)
counties.columns = counties.columns.str.lower()
counties['pct'] = counties['series_complete_pop_pct']
counties['label'] = counties['county'] + ' County, ' + counties['stateabbr']
counties['sfips'] = pd.to_numeric(counties['fips'].str[:2], errors='coerce')
counties['fips'] = pd.to_numeric(counties['fips'], errors='coerce')
state_map = counties[['statename', 'sfips']].drop_duplicates().dropna()

#County Data
us_states = alt.topo_feature(data.us_10m.url, 'states')
states = pd.read_csv('owid_vaccinations.csv').fillna(method='ffill')
states['dt'] = pd.to_datetime(states['date'])
states = states[states['dt'] > '01/08/2021']
states['pct'] = states['people_vaccinated_per_hundred']
states['week'] = states['dt'].dt.week
states.location = states.location.str.replace('New York State', 'New York')
states = states.merge(state_map, left_on='location', right_on='statename', how='left').dropna()
states_raw = states.groupby(['week', 'location']).max().reset_index()
states = states.pivot_table(index=['sfips', 'statename'], columns='week', values='pct', aggfunc='max')
min_week, max_week = states.columns.min(), states.columns.max()
states.columns = states.columns.astype(str)
columns = states.columns.to_list()
states = states.reset_index()

#Demographic Data
demos = pd.read_csv('demographics.csv', skiprows=5).rename(columns={'Demographic Group': 'group', 'Percent of group with at least one dose': 'pct'}).set_index('Date')[['group', 'pct']]
demos['group'] = demos['group'].str.lower()
demos = demos[~demos.group.str.contains('known')].reset_index()
demos.columns = demos.columns.str.lower()
sex = demos[demos.group.str.contains('sex')]
eth = demos[demos.group.str.contains('eth')]
sex.group = sex.group.str.split('_').str[-1]
eth.group = eth.group.str.split('_').str[-1].str.replace('aian', 'asian')
eth = eth.replace({'group': {"nhwhite": "white", "oth": "other", "nhblack":"black", "nhasian": "asian",
                       "nhnhopi": "hawaiian_pi"}})
sex['dt'] = pd.to_datetime(sex.date)
sex = sex[sex['dt'] > '01/08/2021']
sex['week'] = sex['dt'].dt.week
eth['dt'] = pd.to_datetime(eth.date)
eth = eth[eth['dt'] > '01/08/2021']
eth['week'] = eth['dt'].dt.week




#Title and Header
st.title('💉 United States COVID-19 Vaccine Distributions')
st.sidebar.markdown('💉 United States COVID-19 Vaccine 💉')
st.sidebar.markdown(''' 
This app was designed to provide visualizations to different factors of the vaccine distribution in the United States. 

\n

The data comes from **Kaiser Family Foundation** and **Our World in Data**\n

Select which state you would like to visualize \n

All the Charts are interactive. \n

Scroll the mouse over the Charts to feel the interactive features like Tool tip, Zoom, Pan\n
                    
Designed by: 
**Shweta Kumar and Ray Zhao**  ''')


#By Entire Country
st.header("Percentage Vaccinated Per Week by County")
select_week = alt.selection_single(
    name='selected', fields=['week'], init={'week': 2},
    bind=alt.binding_range(min=min_week, max=max_week, step=1)
)

c1a = alt.Chart(us_states).mark_geoshape(
    stroke='black',
    strokeWidth=0.05
).project(
    type='albersUsa'
).transform_lookup(
    lookup='id',
    from_=alt.LookupData(states, 'sfips', ['statename'] + columns)
).transform_fold(
    columns, as_=['week', 'pct']
).transform_calculate(
    week='parseInt(datum.week)',
    pct='isValid(datum.pct) ? datum.pct : -1'  
).encode(
    color=alt.condition(
        'datum.pct > 0',
        alt.Color('pct:Q', scale=alt.Scale(scheme='yellowgreenblue', domain=(0, 100))),
        alt.value('#DBE9F6')
    ),
    # opacity=alt.condition(click, alt.value(1), alt.value(0)),
    tooltip=['pct:Q', 'statename:N']
).add_selection(
    select_week,
    # click
).properties(
    width=700,
    height=400
).transform_filter(
    select_week
)


click = alt.selection_multi(fields=['statename'])
c1b = alt.Chart(us_counties).mark_geoshape(
    stroke='black',
    strokeWidth=0.1,
).project(
    type='albersUsa'
).transform_lookup(
    lookup='id',
    from_=alt.LookupData(counties, 'fips', ['statename', 'pct', 'label'])
).encode(
    color=alt.condition(
        'isValid(datum.pct)',
        alt.Color('pct:Q', scale=alt.Scale(scheme='yellowgreenblue', domain=(0, 100))),
        alt.value('#DBE9F6')
    ),
    opacity=alt.condition(click, alt.value(1), alt.value(0)),
    tooltip=['label:N', 'pct:N']
).add_selection(
    click
).properties(
    width=700,
    height=400
)

c3a = alt.Chart(sex).mark_bar().encode(
    x = alt.X('group:N', axis=alt.Axis(title='Sex')),
    y=alt.Y('pct:Q', scale=alt.Scale(domain=(0, 100)), axis=alt.Axis(title='Percentage Vaccinated')),
    color=alt.Color('group:N', legend=alt.Legend(title="Sex"))
).add_selection(
    select_week
).transform_filter(
    select_week
).interactive()

c3b = alt.Chart(eth).mark_bar().encode(
    x = alt.X('group:N', axis=alt.Axis(title='Ethnicity')),
    y=alt.Y('pct:Q', scale=alt.Scale(domain=(0, 100)), axis=alt.Axis(title='Percentage Vaccinated')),
    color=alt.Color('group:N', legend=alt.Legend(title="Ethnicity"))
).add_selection(
    select_week
).transform_filter(
    select_week
).interactive()

c3 = alt.hconcat(
    c3a, c3b
).resolve_scale(
    color='independent'
)

C = (c1a + c1b)
st.altair_chart(C)

st.header("Select States to Compare Vaccine Distribution Trends")
options = st.multiselect("Select state",states["statename"])
c2 = alt.Chart(states_raw[states_raw["statename"].isin(options)],width=500,height=300).mark_line().encode(
    x=alt.X('week', axis=alt.Axis(title='Week')),
    y=alt.Y('pct', axis=alt.Axis(title='Percentage Vaccinated')),
    color=alt.Color('statename', scale=alt.Scale(domain=click)),
    # opacity=alt.condition(click, alt.value(1), alt.value(0.02)),
).add_selection(
    click
).interactive().properties(
    width=1000,
    height=400
)
st.altair_chart(c2)

st.header("Compare Weekly Percent Vaccinated by Demographics")
op = st.radio("Select the option",('Race', 'Gender'))

if op == 'Gender':
     st.altair_chart(c3a)
elif op == 'Race':
    st.altair_chart(c3b)








