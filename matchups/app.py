import pandas as pd
import plot as wsba_plt
import numpy as np
import plotly.graph_objects as go
from urllib.parse import *
from shiny import *
from shinywidgets import output_widget, render_widget

app_ui = ui.page_fluid(
    ui.tags.style(
    "body {background:#09090b"
    "}"
    ),
    output_widget("plot_matchup"),
)

def server(input, output, session):
    @output()
    @render_widget
    def plot_matchup():
        #Retreive query parameters
        search = session.input[".clientdata_url_search"]()
        query = parse_qs(urlparse(search).query)
        
        print(query)
        #If no input data is provided automatically provide a select skater and plot all 5v5 fenwick shots
        #If no input data is provided automatically provide a select skater and plot all 5v5 fenwick shots
        defaults = {
            'seasona':['20242025,20242025'],
            'teama':['EDM,FLA'],
            'strength_state':['5v5'],
            'season_type':['2']
        }
        
        for key in defaults.keys():
            if key not in query.keys():
                query.update({key:defaults[key]})
        
        #Iterate through query and parse params with multiple selections
        for param in query.keys():
            q_string = query[param][0]
            query[param] = q_string.split(',')

        for i in range(2):
            query[f'team_{i+1}'] = [query['teams'][i]]
            query[f'season_{i+1}'] = [query['seasons'][i]]

        print(query)
        season_1 = query['season_1'][0]
        season_2 = query['season_2'][0]
        #Load appropriate dataframes
        if season_1 == season_2:
            df_1 = pd.read_parquet(f'https://f005.backblazeb2.com/file/weakside-breakout/pbp/{season_1}.parquet')
            df_2 = df_1

        else:
            df_1 = pd.read_parquet(f'https://f005.backblazeb2.com/file/weakside-breakout/pbp/{season_1}.parquet')
            df_2 = pd.read_parquet(f'https://f005.backblazeb2.com/file/weakside-breakout/pbp/{season_2}.parquet')
        
        events = ['missed-shot','shot-on-goal','goal']
        team_xg = {}
        for team, season, df, flip in [(query['team_1'][0],season_1,df_1,True),(query['team_2'][0],season_2,df_2,False)]:
            #Prepare dataframe for plotting based on URL parameters
            df = df.loc[(df['season'].astype(str) == season)&(df['season_type'].astype(str).isin(query['season_type']))].replace({np.nan: None})

            team_xg.update({team:{'for':wsba_plt.heatmap_prep(df,team,events,query['strength_state'],'for',flip=flip),
                                  'against':wsba_plt.heatmap_prep(df,team,events,query['strength_state'],'against',flip=flip)}})
            
        #Left is team_1 for vs team_2 against; Right is team_2 for vs team_1 against
        left_diff = team_xg[query['team_1'][0]]['for']-team_xg[query['team_2'][0]]['against']
        right_diff = team_xg[query['team_2'][0]]['for']-team_xg[query['team_1'][0]]['against']

        rink = wsba_plt.wsba_rink()

        for difference,x_min,x_max in [(left_diff,-100,0),(right_diff,0,100)]:
            data_min= difference.min()
            data_max= difference.max()
        
            if abs(data_min) > data_max:
                data_max = data_min * -1
            elif data_max > abs(data_min):
                data_min = data_max * -1

            fig = go.Figure(
                data = go.Contour(  x=np.linspace(x_min,x_max,(x_max-x_min)),
                                    y=np.linspace(-42.5,42.5,85),
                                    z=difference,
                                    colorscale=[[0.0,'red'],[0.5,'#09090b'],[1.0,'blue']],
                                    connectgaps=True,
                                    contours=dict(
                                        type='levels',
                                        start = data_min,
                                        end = data_max,
                                        size=(data_max-data_min)/11
                                    ),
                                    colorbar=dict(
                                        len = 0.7,
                                        orientation='h',
                                        showticklabels=False,
                                        thickness=15,
                                        yref='paper',
                                        yanchor='top',
                                        y=0
                                    ))
                )
            for trace in fig.data:
                rink.add_trace(trace)
        
        team_1 = query['team_1'][0]
        team_2 = query['team_2'][0]
        strengths = 'All Situations' if len(query['strength_state']) == 4 else query['strength_state']
        span = 'Regular Season' if query['season_type'][0]=='2' else 'Playoffs'
        

        return rink.update_layout( 
                    title=dict(
                        text=f'{team_1} ({season_1}, {span}) vs {team_2} ({season_2}, {span}): xG at {strengths}',
                        x=0.5, y=0.96,
                        xanchor='center',
                        yanchor='top',
                        font=dict(color='white')
                    ),
                ).add_annotation(
                    text='Lower xG',
                    xref="paper",
                    yref="paper",
                    xanchor='right',
                    yanchor='top',
                    font=dict(color='white'),
                    x=0.3,
                    y=0.04,
                    showarrow=False
                ).add_annotation(
                    text='Higher xG',
                    xref="paper",
                    yref="paper",
                    xanchor='right',
                    yanchor='top',
                    font=dict(color='white'),
                    x=0.76,
                    y=0.04,
                    showarrow=False
                )

app = App(app_ui, server)