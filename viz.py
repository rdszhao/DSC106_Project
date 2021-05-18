# %%
import altair as alt
import data

# DATA RETRIEVAL
us = data.geoshapes()
counties = data.counties()
state_map = data.state_map(counties)
states = data.states(state_map)
hes = data.hesitancy(state_map)
demos = data.demographics()

# WEEK SLIDER
select_week = alt.selection_single(
    name='week', fields=['week'], init={'week': 2},
    bind=alt.binding_range(min=states.min_week, max=states.max_week, step=1)
)

# STATE VACCINATION CHOROPLETH
c1a = alt.Chart(us.states).mark_geoshape(
    stroke='black',
    strokeWidth=0.05
).project(
    type='albersUsa'
).transform_lookup(
    lookup='id',
    from_=alt.LookupData(states.wide, 'sfips', ['statename'] + states.columns)
).transform_fold(
    states.columns, as_=['week', 'pct']
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

# CLICK STATE SELECTOR
click = alt.selection_multi(fields=['statename'])

# COUNTY VACCINATION CHOROPLETH
c1b = alt.Chart(us.counties).mark_geoshape(
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

# STATE VACCINATION LINE PLOT
c2 = alt.Chart(states.long).mark_line().encode(
    x='week:N',
    y='pct:Q',
    color=alt.Color('statename', scale=alt.Scale(domain=click)),
    # opacity=alt.condition(click, alt.value(1), alt.value(0.02)),
).add_selection(
    click
).interactive().properties(
    width=1000,
    height=400
)

# SEX VACCINATION BAR CHART
c3a = alt.Chart(demos.sex).mark_bar().encode(
    x='group:N',
    y=alt.Y('pct:Q', scale=alt.Scale(domain=(0, 100))),
    color=alt.Color('group:N')
).add_selection(
    select_week
).transform_filter(
    select_week
)

# ETHNICITY VACCINATION BAR CHART
c3b = alt.Chart(demos.eth).mark_bar().encode(
    x='group:N',
    y=alt.Y('pct:Q', scale=alt.Scale(domain=(0, 100))),
    color=alt.Color('group:N'),
).add_selection(
    select_week
).transform_filter(
    select_week
)

c3 = alt.hconcat(
    c3a, c3b
).resolve_scale(
    color='independent'
)

C1 = ((c1a + c1b) | c3) & c2

# HESITANCY COUNTY CHOROPLETH
c4a = alt.Chart(us.states).mark_geoshape(
    stroke='black',
    strokeWidth=0.05
).project(
    type='albersUsa'
).transform_lookup(
    lookup='id',
    from_=alt.LookupData(hes.states, 'sfips', ['statename', 'pct'])
).encode(
    color=alt.Color('pct:Q', scale=alt.Scale(scheme='yellowgreenblue', domain=(0, 100))),
    tooltip=['pct:Q', 'statename:N']
).properties(
    width=700,
    height=400
)

# HESITANCY STATE CHOROPLETH
c4b = alt.Chart(us.counties).mark_geoshape(
    stroke='black',
    strokeWidth=0.1,
).project(
    type='albersUsa'
).transform_lookup(
    lookup='id',
    from_=alt.LookupData(hes.county, 'fips', ['statename', 'county', 'pct'])
).encode(
    color=alt.Color('pct:Q', scale=alt.Scale(scheme='yellowgreenblue', domain=(0, 100))),
    opacity=alt.condition(click, alt.value(1), alt.value(0)),
    tooltip=['county:N', 'pct:N']
).add_selection(
    click
).properties(
    width=700,
    height=400
)

# HESISTANCY CHOROPLETH
C2 = c4a + c4b

C1
C2