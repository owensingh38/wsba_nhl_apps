import pandas as pd
import numpy as np
from urllib.parse import *
from shiny import *
from shinywidgets import output_widget, render_widget 
from name_fix import *

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
            --bs-table-bg: #09090b;
            --bs-table-color-state: white;
        }

        .table thead tr th {
            white-space: nowrap;
            text-align: center;
            color: white;
            background-color: #09090b;
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

        .table thead th {
            text-align: center !important;
        }
    """
    ),
    ui.tags.h2(ui.output_text('game_header'), style="text-align: center;"),
    ui.tags.h4('Team Stats'),
    ui.output_data_frame("team_stats"),
    ui.tags.h4('Scoring Summary'),
    ui.output_data_frame("scoring_summary"),
    ui.output_ui("table_filters"),
    ui.row(
        ui.column(6, ui.tags.h4(ui.output_text('away_header'))),
        ui.column(6, ui.tags.h4(ui.output_text('home_header')))
    ),
    ui.row(
        ui.column(6, ui.output_data_frame("away_stats")),
        ui.column(6, ui.output_data_frame("home_stats"))
    ),
    ui.row(
        ui.column(6, ui.tags.h4(ui.output_text('away_goalie_header'))),
        ui.column(6, ui.tags.h4(ui.output_text('home_goalie_header')))
    ),
    ui.row(
        ui.column(6, ui.output_data_frame("away_goalie")),
        ui.column(6, ui.output_data_frame("home_goalie"))
    )
)

def server(input, output, session):
    query = reactive.Value(None)
    game_info = reactive.Value(None)

    def get_schedule():
        games = pd.read_csv('https://f005.backblazeb2.com/file/weakside-breakout/info/schedule.csv')
        
        return games.loc[games['gameState'].isin(['OFF','FINAL'])]

    @reactive.Effect
    def query_params():
        #Retreive query parameters
        search = session.input[".clientdata_url_search"]()
        q = parse_qs(urlparse(search).query)

        print(q)

        defaults = {
            'game_id':['2024020001'],
        }

        for key in defaults.keys():
            if key not in q.keys():
                q.update({key:defaults[key]})

        query.set(q)
        
    def active_params():
        return query.get() or {}

    @reactive.Effect
    def get_game_info():
        #Load params
        query = active_params()

        #Load game data
        game = get_schedule()
        game = game.loc[game['id'].astype(str).str.replace('.0','')==query['game_id'][0]]

        game_info.set({
            'game_id':game['id'].iloc[0],
            'season':game['season'].iloc[0],
            'title':game['game_title'].iloc[0],
            'date':game['date'].iloc[0],
            'away_team_abbr':game['away_team_abbr'].iloc[0],
            'home_team_abbr':game['home_team_abbr'].iloc[0],
            'away_logo':game['awayTeam.darkLogo'].iloc[0],
            'home_logo':game['homeTeam.darkLogo'].iloc[0],
            'away_score':game['awayTeam.score'].iloc[0],
            'home_score':game['homeTeam.score'].iloc[0],
        })
        print(game_info.get())

    game_df = reactive.Value(None)
    @reactive.Effect
    def active_game():
        #Determine which season to load based on the input game_id
        info = game_info.get()
        season = info['season']
        #Load appropriate dataframe
        df = pd.read_parquet(f'https://f005.backblazeb2.com/file/weakside-breakout/game_log/wsba_nhl_{season}_game_log.parquet')
        goalie_df = pd.read_parquet(f'https://f005.backblazeb2.com/file/weakside-breakout/game_log/goalie/wsba_nhl_{season}_game_log_goalie.parquet')
        pbp = pd.read_parquet(f'https://f005.backblazeb2.com/file/weakside-breakout/pbp/{season}.parquet')

        game_df.set([df.loc[(df['Game']==info['game_id'])], pbp.loc[(pbp['game_id']==info['game_id'])&(pbp['event_type']=='goal')], goalie_df.loc[(goalie_df['Game']==info['game_id'])]])

    @output
    @render.ui
    def table_filters():
        all_strengths = ['4v5','5v4','5v5','Other','All']
        return ui.panel_well(
            ui.tags.div(
            {"class": "form-row custom-input"},
                ui.input_selectize('stat_type','Type',['Individual','On-Ice']),
                ui.input_selectize('strength_state','Strength',all_strengths,selected='5v5'),
            )
        )

    @output
    @render.data_frame
    def team_stats():
        df = game_df.get()[0]
        info = game_info.get()

        df = df.loc[df['Strength']=='All'].groupby('Team').agg(
            Fenwick=('Fi','sum'),
            xG=('xGi','sum'),
            Hits=('HF','sum'),
            Give=('Give','sum'),
            Take=('Take','sum'),
            PIM=('PIM','sum')
        ).reset_index()

        score = pd.DataFrame([[info['away_team_abbr'],
                               info['away_score']],
                               [info['home_team_abbr'],
                               info['home_score']]],columns=['Team','Goals'])
        
        df = pd.merge(df,score,how='left')
        df = df[['Team','Goals','Fenwick','xG','Hits','Give','Take','PIM']]

        df['xG'] = df['xG'].round(2)

        print(df)

        return render.DataTable(df,height='fit-content')

    @output
    @render.data_frame
    def scoring_summary():
        pbp = game_df.get()[1]
 
        pbp = pbp[['event_num','period','seconds_elapsed','strength_state','description','away_score','home_score','xG']].rename(columns={
                    'event_num':'#',
                    'seconds_elapsed':'Seconds',
                    'strength_state':'Strength State',
                    'away_score':'Away Score',
                    'home_score':'Home Score'
                })
                
        pbp['xG'] = (pbp['xG']*100).round(4)

        return render.DataTable(pbp, height='fit-content')

    @output
    @render.text
    def game_header():
        return game_info.get()['title']

    @output
    @render.text
    def away_header():
        team = game_info.get()['away_team_abbr']

        return f'{team} Stats'

    @output
    @render.text
    def home_header():
        team = game_info.get()['home_team_abbr']

        return f'{team} Stats'

    @output
    @render.text
    def away_goalie_header():
        team = game_info.get()['away_team_abbr']

        return f'{team} Goalie Stats'

    @output
    @render.text
    def home_goalie_header():
        team = game_info.get()['home_team_abbr']

        return f'{team} Goalie Stats'
    
    @output
    @render.data_frame
    def away_stats():
        df = game_df.get()[0]
        info = game_info.get()

        if input.stat_type() == 'Individual':
            cols = [
                'Player','ID','Position','Handedness','TOI','Gi','A1','A2','P1','P','Give','Take','HF','HA',
                'Fi','xGi'
            ]
        else:
            cols = [
                'Player','ID','Position','Handedness','TOI','GF','GA','FF','FA','xGF','xGA','GF%','FF%','xGF%'
            ]

        df = df.loc[(df['Team']==info['away_team_abbr'])&(df['Strength']==input.strength_state()),cols]

        for col in ['TOI','xGi','xGF','xGA','GF%','FF%','xGF%']:
            try:
                if '%' in col:
                    df[col] = (df[col]*100).round(2).astype(str) + '%'
                else:
                    df[col] = df[col].round(2)
            except:
                continue
        
        df = fix_names(df)

        return render.DataTable(df.rename(columns={
            'Gi':'G',
            'Fi':'iFF',
            'xGi':'ixG'
        }).drop(columns=['ID']).rename(columns={'Position':'POS','Handedness':'Hand'}))
    
    @output
    @render.data_frame
    def home_stats():
        df = game_df.get()[0]
        info = game_info.get()

        if input.stat_type() == 'Individual':
            cols = [
                'Player','ID','TOI','Position','Handedness','Gi','A1','A2','P1','P','Give','Take','HF','HA',
                'Fi','xGi'
            ]
        else:
            cols = [
                'Player','ID','TOI','Position','Handedness','GF','GA','FF','FA','xGF','xGA','GF%','FF%','xGF%'
            ]

        df = df.loc[(df['Team']==info['home_team_abbr'])&(df['Strength']==input.strength_state()),cols]

        for col in ['TOI','xGi','xGF','xGA','GF%','FF%','xGF%']:
            try:
                if '%' in col:
                    df[col] = (df[col]*100).round(2).astype(str) + '%'
                else:
                    df[col] = df[col].round(2)
            except:
                continue
        
        df = fix_names(df)

        return render.DataTable(df.rename(columns={
            'Gi':'G',
            'Fi':'iFF',
            'xGi':'ixG'
        }).drop(columns=['ID']).rename(columns={'Position':'POS','Handedness':'Hand'}))

    @output
    @render.data_frame
    def away_goalie():
        df = game_df.get()[2]
        info = game_info.get()

        cols = [
            'Goalie','ID','TOI','Position','Handedness','GA','FA','xGA','GSAx'
        ]

        df = df.loc[(df['Team']==info['away_team_abbr'])&(df['Strength']==input.strength_state()),cols]

        for col in ['TOI','xGA','GSAx']:
            try:
                if '%' in col:
                    df[col] = (df[col]*100).round(2).astype(str) + '%'
                else:
                    df[col] = df[col].round(2)
            except:
                continue
        
        df = fix_names(df,'Goalie')

        return render.DataTable(df.drop(columns=['ID']).rename(columns={'Position':'POS','Handedness':'Hand'}))
    
    @output
    @render.data_frame
    def home_goalie():
        df = game_df.get()[2]
        info = game_info.get()

        cols = [
            'Goalie','ID','TOI','Position','Handedness','GA','FA','xGA','GSAx'
        ]

        df = df.loc[(df['Team']==info['home_team_abbr'])&(df['Strength']==input.strength_state()),cols]

        for col in ['TOI','xGA','GSAx']:
            try:
                if '%' in col:
                    df[col] = (df[col]*100).round(2).astype(str) + '%'
                else:
                    df[col] = df[col].round(2)
            except:
                continue
        
        df = fix_names(df,'Goalie')

        return render.DataTable(df.drop(columns=['ID']).rename(columns={'Position':'POS','Handedness':'Hand'}))
    
app = App(app_ui, server)