{
 "metadata": {
  "language_info": {
   "codemirror_mode": {
    "name": "ipython",
    "version": 3
   },
   "file_extension": ".py",
   "mimetype": "text/x-python",
   "name": "python",
   "nbconvert_exporter": "python",
   "pygments_lexer": "ipython3",
   "version": "3.6.12"
  },
  "orig_nbformat": 2,
  "kernelspec": {
   "name": "python3612jvsc74a57bd0344443636c3027c5042750c9c609acdda283a9c43681b128a8c1053e7ad2aa7d",
   "display_name": "Python 3.6.12 64-bit ('base': conda)"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 2,
 "cells": [
  {
   "cell_type": "code",
   "execution_count": 2,
   "metadata": {},
   "outputs": [],
   "source": [
    "import pandas as pd\n",
    "import altair as alt\n",
    "import json\n",
    "import requests\n",
    "from vega_datasets import data"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 3,
   "metadata": {},
   "outputs": [],
   "source": [
    "us_counties = alt.topo_feature(data.us_10m.url, 'counties')\n",
    "counties_src = 'https://covid.cdc.gov/covid-data-tracker/COVIDData/getAjaxData?id=vaccination_county_condensed_data'\n",
    "resp = requests.get(counties_src)\n",
    "raw = json.loads(resp.text)\n",
    "counties = pd.DataFrame(raw['vaccination_county_condensed_data']).fillna(-1)\n",
    "counties.columns = counties.columns.str.lower()\n",
    "counties['pct'] = counties['series_complete_pop_pct']\n",
    "counties['label'] = counties['county'] + ' County, ' + counties['stateabbr']\n",
    "counties['sfips'] = pd.to_numeric(counties['fips'].str[:2], errors='coerce')\n",
    "counties['fips'] = pd.to_numeric(counties['fips'], errors='coerce')\n",
    "state_map = counties[['statename', 'sfips']].drop_duplicates().dropna()"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 4,
   "metadata": {},
   "outputs": [],
   "source": [
    "us_states = alt.topo_feature(data.us_10m.url, 'states')\n",
    "states = pd.read_csv('data/owid_vaccinations.csv').fillna(method='ffill')\n",
    "states['dt'] = pd.to_datetime(states['date'])\n",
    "states = states[states['dt'] > '01/08/2021']\n",
    "states['pct'] = states['people_vaccinated_per_hundred']\n",
    "states['week'] = states['dt'].dt.isocalendar().week\n",
    "states = states.merge(state_map, left_on='location', right_on='statename', how='left')\n",
    "states_raw = states.groupby(['week', 'location']).max().reset_index()\n",
    "states = states.pivot_table(index=['sfips', 'statename'], columns='week', values='pct', aggfunc='max')\n",
    "min_week, max_week = states.columns.min(), states.columns.max()\n",
    "states.columns = states.columns.astype(str)\n",
    "columns = states.columns.to_list()\n",
    "states = states.reset_index()"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 5,
   "metadata": {},
   "outputs": [],
   "source": [
    "select_week = alt.selection_single(\n",
    "    name='week', fields=['week'], init={'week': 2},\n",
    "    bind=alt.binding_range(min=min_week, max=max_week, step=1)\n",
    ")\n",
    "\n",
    "c1 = alt.Chart(us_states).mark_geoshape(\n",
    "    stroke='black',\n",
    "    strokeWidth=0.05\n",
    ").project(\n",
    "    type='albersUsa'\n",
    ").transform_lookup(\n",
    "    lookup='id',\n",
    "    from_=alt.LookupData(states, 'sfips', ['statename'] + columns)\n",
    ").transform_fold(\n",
    "    columns, as_=['week', 'pct']\n",
    ").transform_calculate(\n",
    "    week='parseInt(datum.week)',\n",
    "    pct='isValid(datum.pct) ? datum.pct : -1'  \n",
    ").encode(\n",
    "    color=alt.condition(\n",
    "        'datum.pct > 0',\n",
    "        alt.Color('pct:Q', scale=alt.Scale(scheme='yellowgreenblue', domain=(0, 100))),\n",
    "        alt.value('#DBE9F6')\n",
    "    ),\n",
    "    # opacity=alt.condition(click, alt.value(1), alt.value(0)),\n",
    "    tooltip=['pct:Q', 'statename:N']\n",
    ").add_selection(\n",
    "    select_week,\n",
    "    # click\n",
    ").properties(\n",
    "    width=700,\n",
    "    height=400\n",
    ").transform_filter(\n",
    "    select_week\n",
    ")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 6,
   "metadata": {},
   "outputs": [],
   "source": [
    "click = alt.selection_multi(fields=['statename'])\n",
    "c2 = alt.Chart(us_counties).mark_geoshape(\n",
    "    stroke='black',\n",
    "    strokeWidth=0.1,\n",
    ").project(\n",
    "    type='albersUsa'\n",
    ").transform_lookup(\n",
    "    lookup='id',\n",
    "    from_=alt.LookupData(counties, 'fips', ['statename', 'pct', 'label'])\n",
    ").encode(\n",
    "    color=alt.condition(\n",
    "        'isValid(datum.pct)',\n",
    "        alt.Color('pct:Q', scale=alt.Scale(scheme='yellowgreenblue', domain=(0, 100))),\n",
    "        alt.value('#DBE9F6')\n",
    "    ),\n",
    "    opacity=alt.condition(click, alt.value(1), alt.value(0)),\n",
    "    tooltip=['label:N', 'pct:N']\n",
    ").add_selection(\n",
    "    click\n",
    ").properties(\n",
    "    width=700,\n",
    "    height=400\n",
    ")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 7,
   "metadata": {},
   "outputs": [],
   "source": [
    "c3 = alt.Chart(states_raw).mark_line().encode(\n",
    "    x='week:N',\n",
    "    y='pct:Q',\n",
    "    color=alt.Color('statename', scale=alt.Scale(domain=click)),\n",
    "    # opacity=alt.condition(click, alt.value(1), alt.value(0.02)),\n",
    ").add_selection(\n",
    "    click\n",
    ").interactive().properties(\n",
    "    width=700,\n",
    "    height=400\n",
    ")"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": 8,
   "metadata": {},
   "outputs": [
    {
     "output_type": "execute_result",
     "data": {
      "text/plain": [
       "alt.VConcatChart(...)"
      ]
     },
     "metadata": {},
     "execution_count": 8
    }
   ],
   "source": [
    "(c1 + c2) & c3"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": []
  }
 ]
}