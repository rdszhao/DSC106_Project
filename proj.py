# %%
import pandas as pd
import altair as alt
import json
import requests
from vega_datasets import data
# %%
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
# %%
us_states = alt.topo_feature(data.us_10m.url, 'states')
states = pd.read_csv('data/owid_vaccinations.csv').fillna(method='ffill')
states['dt'] = pd.to_datetime(states['date'])
states = states[states['dt'] > '01/08/2021']
states['pct'] = states['people_vaccinated_per_hundred']
states['week'] = states['dt'].dt.isocalendar().week
states = states.merge(state_map, left_on='location', right_on='statename', how='left')
states_raw = states.groupby(['week', 'location']).max().reset_index()
states = states.pivot_table(index=['sfips', 'statename'], columns='week', values='pct', aggfunc='max')
min_week, max_week = states.columns.min(), states.columns.max()
states.columns = states.columns.astype(str)
columns = states.columns.to_list()
states = states.reset_index()
# %%
select_week = alt.selection_single(
    name='week', fields=['week'], init={'week': 2},
    bind=alt.binding_range(min=min_week, max=max_week, step=1)
)

c1 = alt.Chart(us_states).mark_geoshape(
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
# %%
click = alt.selection_multi(fields=['statename'])
c2 = alt.Chart(us_counties).mark_geoshape(
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
# %%
c3 = alt.Chart(states_raw).mark_line().encode(
    x='week:N',
    y='pct:Q',
    color=alt.Color('statename', scale=alt.Scale(domain=click)),
    # opacity=alt.condition(click, alt.value(1), alt.value(0.02)),
).add_selection(
    click
).interactive().properties(
    width=700,
    height=400
)
# %%
(c1 + c2) & c3
# %%
