import pandas as pd
import plotly.express as px
import plot as wsba_plt
import numpy as np
from urllib.parse import *
from shiny import *
from shinywidgets import output_widget, render_widget 

app_ui = ui.page_fluid(
    ui.tags.link(
        rel='stylesheet',
        href='https://fonts.googleapis.com/css2?family=Bebas+Neue&display=swap'
    ),
    ui.tags.style(
        """
        body {
            background-color: #09090b;
            color: white;
            font-family: 'Bebas Neue', sans-serif;
        }

        .custom-input input.form-control,
        .custom-input .selectize-control,
        .custom-input .selectize-input {
            background-color: #09090b !important;  /* black background */
            color: white !important;               /* white font color */
            border-radius: 4px;
            border: 1px solid #444;
        }

        .custom-input .selectize-dropdown,
        .custom-input .selectize-dropdown-content {
            background-color: #09090b !important;
            color: white !important;
        }          

        .custom-input .selectize-control.multi .item {
            background-color: #09090b !important;
            color: white !important;
            border-radius: 4px;
            padding: 2px 6px;
            margin: 2px 4px 2px 0;
        }

        label.control-label {
            color: white !important;
        }   

        .selectize-control.multi {
            width: 300px !important;
        }

        .form-row {
            display: flex;
            gap: 12px;
            flex-wrap: wrap;
            justify-content: center;
        }

        .submit-button {
            display: flex;
            justify-content: center;
        }

        .hide {
            display: none;
        }

        .table thead tr {
            white-space: nowrap;
            text-align: center;
            color: white;
            background-color: #09090b;
        }

        .table thead th {
            white-space: nowrap;
            text-align: center;
            color: #09090b;
        }

        .table tbody tr {
            --bs-table-bg: #09090b;
            --bs-table-color-state: white;
        }

        .table tbody tr td {
            white-space: nowrap;
            text-align: center;
            overflow: hidden;
            text-overflow: ellipsis;
            color: white;
            background-color: #09090b;
        }
    """
    ),
    output_widget("line_combos"),
    ui.output_data_frame("with_out")
)

def server(input, output, session):
    queries = reactive.Value({})
    team_data = reactive.Value(pd.DataFrame())
    player_data = reactive.Value(pd.DataFrame())

    col = [
        'season','season_type','game_id','game_date',
        'away_team_abbr','home_team_abbr','event_num','period',
        'seconds_elapsed',"strength_state","strength_state_venue",
        "event_type","description",
        "penalty_duration",
        "event_team_abbr","event_team_venue",
        "x_adj","y_adj",
        "event_distance","event_angle","event_length","seconds_since_last",
        "away_on_1_id","away_on_2_id","away_on_3_id","away_on_4_id","away_on_5_id","away_on_6_id","away_goalie_id",
        "home_on_1_id","home_on_2_id","home_on_3_id","home_on_4_id","home_on_5_id","home_on_6_id","home_goalie_id",
        'rush','rebound','empty_net','xG'
    ]

    @output()
    @render_widget
    def line_combos():
        #Retreive query parameters
        search = session.input[".clientdata_url_search"]()
        query = parse_qs(urlparse(search).query)
        
        print(query)
        #If no input data is provided automatically provide a select skater and plot all 5v5 fenwick shots
        defaults = {
            'season':['20182019'],
            'team':['BOS'],
            'strength_state':['5v5'],
            'season_type':['2'],
            'skaters':['8473419,8470638']
        }
        
        for key in defaults.keys():
            if key not in query.keys():
                query.update({key:defaults[key]})

        #Iterate through query and parse params with multiple selections
        for param in query.keys():
            q_string = query[param][0]
            query[param] = q_string.split(',')

        print(query)
        #Determine which season to load based on the input
        season = query['season'][0]
        queries.set(query)

        #Load appropriate dataframe
        df = pd.read_parquet(f'https://weakside-breakout.s3.us-east-2.amazonaws.com/pbp/parquet/nhl_pbp_{season}.parquet')
    
        #Prepare dataframe for plotting based on URL parameters
        df = df.loc[(df['season_type'].astype(str).isin(query['season_type']))][col]
        team_data.set(df[(df['away_team_abbr']==query['team'][0]) | (df['home_team_abbr']==query['team'][0])])
        player_data.set(wsba_plt.player_events(df,query['skaters']))

        #Return empty rink if no data exists else continue
        if df.empty:
            return wsba_plt.wsba_rink()
        else:
            rink = wsba_plt.wsba_rink()

            try:
                for_plot = wsba_plt.heatmap(df,team=query['team'][0],skaters=query['skaters'],events=['missed-shot','shot-on-goal','goal'],strengths=query['strength_state'],onice='for')
                against_plot = wsba_plt.heatmap(df,team=query['team'][0],skaters=query['skaters'],events=['missed-shot','shot-on-goal','goal'],strengths=query['strength_state'],onice='against')

                for trace in for_plot[1].data:
                    rink.add_trace(trace)
                
                for trace in against_plot[1].data:
                    rink.add_trace(trace)

                season = int(season[0:4])

                return rink.add_annotation(
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
            except:
                return wsba_plt.wsba_rink()
    
    @output()
    @render.data_frame
    def with_out():
        query_load = queries.get()

        ids = query_load['skaters']
        team = query_load['team'][0]
        team_pbp = team_data.get()
        team_pbp['home_on_ice'] = team_pbp['home_on_1_id'].astype(str) + ";" + team_pbp['home_on_2_id'].astype(str) + ";" + team_pbp['home_on_3_id'].astype(str) + ";" + team_pbp['home_on_4_id'].astype(str) + ";" + team_pbp['home_on_5_id'].astype(str) + ";" + team_pbp['home_on_6_id'].astype(str)
        team_pbp['away_on_ice'] = team_pbp['away_on_1_id'].astype(str) + ";" + team_pbp['away_on_2_id'].astype(str) + ";" + team_pbp['away_on_3_id'].astype(str) + ";" + team_pbp['away_on_4_id'].astype(str) + ";" + team_pbp['away_on_5_id'].astype(str) + ";" + team_pbp['away_on_6_id'].astype(str)

        team_pbp['onice'] = team_pbp['away_on_ice']+';'+team_pbp['home_on_ice']

        if len(ids)>2:
            mask = ((team_pbp['onice'].str.contains(ids[0])) & (team_pbp['onice'].str.contains(ids[1])) & (team_pbp['onice'].str.contains(ids[2])))
        else:
            mask = ((team_pbp['onice'].str.contains(ids[0])) & (team_pbp['onice'].str.contains(ids[1])))
    
        team_pbp = team_pbp.loc[~mask]

        if 'Other' in query_load['strength_state']:
            strength_state = query_load['strength_state'] + team_pbp.loc[~(team_pbp['strength_state'].isin(['5v5','5v4','4v5'])),'strength_state'].drop_duplicates().to_list()
        else:
            strength_state = query_load['strength_state']
        
        with_stats = wsba_plt.calculate_stats(player_data.get(), query_load['team'][0], strength_state).replace({team:f'{team} With'})
        without_stats = wsba_plt.calculate_stats(team_pbp, query_load['team'][0], strength_state).replace({team:f'{team} Without'})

        total = pd.concat([with_stats, without_stats])[['Team',
                                                       'TOI',
                                                       'GF/60','GA/60',
                                                       'SF/60','SA/60',
                                                       'FF/60','FA/60',
                                                       'xGF/60','xGA/60',
                                                       'GF%','SF%',
                                                       'FF%','xGF%',
                                                       'GSAx']].round(2)
        
        return render.DataTable(total)

app = App(app_ui, server)