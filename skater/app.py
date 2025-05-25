import pandas as pd
import plotly.express as px
import plot as wsba_plt
import numpy as np
from urllib.parse import *
from shiny import *
from shinywidgets import output_widget, render_widget 

app_ui = ui.page_fluid(
    ui.tags.style(
    "body {background:#09090b"
    "}"
    ),
    output_widget("plot_skater"),
)

def server(input, output, session):
    @output()
    @render_widget
    def plot_skater():
        #Retreive query parameters
        search = session.input[".clientdata_url_search"]()
        query = parse_qs(urlparse(search).query)
        
        print(query)
        #If no input data is provided automatically provide a select skater and plot all 5v5 fenwick shots
        if 'event_type' not in query.keys() or 'strength_state' not in query.keys():
            if 'skater' not in query.keys():
                query = {'skater':['8473419'],'season':['20182019'],'team':['BOS'],'event_type':['missed-shot,shot-on-goal,goal'],'strength_state':['5v5']}
            else:
                query.update({'event_type':['missed-shot,shot-on-goal,goal'],'strength_state':['5v5']})

        #Iterate through query and parse params with multiple selections
        for param in query.keys():
            q_string = query[param][0]
            query[param] = q_string.split(',')

        print(query)
        #Determine which season to load based on the input
        season = query['season'][0]
        #Load appropriate dataframe
        df = pd.read_parquet(f'https://f005.backblazeb2.com/file/weakside-breakout/pbp/{season}.parquet')
    
        #Prepare dataframe for plotting based on URL parameters
        df = df.loc[(df['event_player_1_id'].astype(str).str.replace('.0','').isin(query['skater']))&(df['season'].astype(str).isin(query['season']))&(df['event_team_abbr'].astype(str).isin(query['team']))].replace({np.nan: None})
        df = wsba_plt.prep(df,events=query['event_type'],strengths=query['strength_state'])

        #Return empty rink if no data exists else continue
        if df.empty:
            return wsba_plt.wsba_rink(setting='offense',vertical=True)
        else:
            colors = wsba_plt.colors(df)
            rink = wsba_plt.wsba_rink(setting='offense',vertical=True)

            plot = px.scatter(df,
                              x='x', y='y',
                              size='size',
                              color='Team',
                              color_discrete_map=colors,
                              hover_name='Description',
                              hover_data=['Event Num.', 'Period', 'Time (in seconds)',
                                          'Strength',
                                          'Away Score', 'Home Score', 'x', 'y',
                                          'Event Distance from Attacking Net',
                                          'Event Angle to Attacking Net',
                                          'xG'])

            for trace in plot.data:
                rink.add_trace(trace)

            return rink

app = App(app_ui, server)