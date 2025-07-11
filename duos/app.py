import pandas as pd
import pyarrow.dataset as ds
import numpy as np
import calc
import requests as rs
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
    ui.output_data_frame("duos")
)

def server(input, output, session):
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
    @render.data_frame
    def duos():
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

        #Load appropriate dataframe
        dataset = ds.dataset(f's3://weakside-breakout/pbp/parquet/nhl_pbp_{season}.parquet', format='parquet')
        filter_expr = ((ds.field('away_team_abbr') == query['team'][0]) | (ds.field('home_team_abbr') == query['team'][0])) & ((ds.field('season_type') == int(query['season_type'][0])))

        table = dataset.to_table(columns=col,filter=filter_expr)
        df = table.to_pandas()

        #Prepare dataframe
        df['home_on_ice'] = df['home_on_1_id'].astype(str) + ";" + df['home_on_2_id'].astype(str) + ";" + df['home_on_3_id'].astype(str) + ";" + df['home_on_4_id'].astype(str) + ";" + df['home_on_5_id'].astype(str) + ";" + df['home_on_6_id'].astype(str)
        df['away_on_ice'] = df['away_on_1_id'].astype(str) + ";" + df['away_on_2_id'].astype(str) + ";" + df['away_on_3_id'].astype(str) + ";" + df['away_on_4_id'].astype(str) + ";" + df['away_on_5_id'].astype(str) + ";" + df['away_on_6_id'].astype(str)

        df['onice_for'] = np.where(df['home_team_abbr']==df['event_team_abbr'],df['home_on_ice'],df['away_on_ice'])
        df['onice_against'] = np.where(df['away_team_abbr']==df['event_team_abbr'],df['home_on_ice'],df['away_on_ice'])

        df['onice'] = df['onice_for'] + ';' + df['onice_against']
        
        skaters = query['skaters']
        #Four aggregations to be completed:
        #Team with both players on the ice
        #Team with each player on the ice without the other
        #Team with neither player on the ice
        both = df.loc[(df['onice'].str.contains(skaters[0]))&(df['onice'].str.contains(skaters[1]))]
        p1 = df.loc[(df['onice'].str.contains(skaters[0]))&(~(df['onice'].str.contains(skaters[1])))]
        p2 = df.loc[(~(df['onice'].str.contains(skaters[0])))&(df['onice'].str.contains(skaters[1]))]
        neither = df.loc[~((df['onice'].str.contains(skaters[0]))&(df['onice'].str.contains(skaters[1])))]

        dfs = []
        if 'Other' in query['strength_state']:
            strength_state = query['strength_state'] + df.loc[~(df['strength_state'].isin(['5v5','5v4','4v5'])),'strength_state'].drop_duplicates().to_list()
        else:
            strength_state = query['strength_state']
        
        skater_names = {}
        #Find player names
        for i in range(2):
            skater = skaters[i]
            data = rs.get(f'https://api-web.nhle.com/v1/player/{skater}/landing').json()

            name = data['firstName']['default'].upper() + ' ' + data['lastName']['default'].upper()

            skater_names.update({f'skater{i+1}':name})

        team = query['team'][0]
        
        #Calculate stats for each df
        skater1 = skater_names['skater1']
        skater2 = skater_names['skater2']

        for df, data in zip([both, p1, p2, neither],['With Both',f'With {skater1}, Without {skater2}',f'With {skater2}, Without {skater1}','With Neither']):
            stats = calc.calculate_stats(df,team,strength_state).replace({team: f'{team} {data}'})
            dfs.append(stats)

        total = pd.concat(dfs)[['Team',
                                'TOI',
                                'GF/60','GA/60',
                                'SF/60','SA/60',
                                'FF/60','FA/60',
                                'xGF/60','xGA/60',
                                'GF%','SF%',
                                'FF%','xGF%',
                                'GSAx']].round(2)
        
        return render.DataGrid(total)

app = App(app_ui, server)