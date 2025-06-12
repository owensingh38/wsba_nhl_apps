import pandas as pd
import plotly.express as px
import plot as wsba_plt
import numpy as np
from urllib.parse import *
from shiny import *
from shinywidgets import output_widget, render_widget 

app_ui = ui.page_fluid(
    ui.tags.style(
        """
        body {
            background-color: #09090b;
            color: white;
            font-family: 'Segoe UI', sans-serif;
        }

        .custom-input {
            background-color: #111113;
            border: 1px solid #2a2a2d;
            color: white;
            padding: 6px 12px;
            border-radius: 8px;
            margin-right: 10px;
            min-width: 160px;
            font-weight: 600;
            box-shadow: 0 0 6px rgba(0,0,0,0.2);
        }

        .custom-input:focus {
            outline: none;
            border-color: #444;
            box-shadow: 0 0 4px #3b82f6;
        }

        .panel-well {
            background-color: #111113 !important;
            border: 1px solid #2a2a2d;
            border-radius: 12px;
            padding: 20px;
            box-shadow: 0 0 10px rgba(0,0,0,0.3);
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
    """
    ),
    ui.output_ui('add_filters'),
    output_widget("plot_game"),
)

def server(input, output, session):
    query = reactive.Value(None)

    @reactive.Effect
    def query_params():
        #Retreive query parameters
        search = session.input[".clientdata_url_search"]()
        q = parse_qs(urlparse(search).query)
        
        print(q)
        #If no input data is provided automatically provide a select game and plot all 5v5 fenwick shots
        defaults = {
            'game_id':['2024021000'],
            'event_type':['missed-shot,shot-on-goal,goal'],
            'strength_state':['all'],
            'filters':['false']
        }

        for key in defaults.keys():
            if key not in q.keys():
                q.update({key:defaults[key]})

        #Add filters if necessary
        try: q['filters']
        except:
            q.update({'filters':['false']})
        
        query.set(q)
    
    def schedule():
        return pd.read_csv('https://f005.backblazeb2.com/file/weakside-breakout/info/schedule.csv')
    
    def active_params():
        return query.get() or {}

    @output
    @render.ui
    def add_filters():
        query = active_params()

        games = schedule() 
        game_title = games.loc[games['id'].astype(str)==query['game_id'][0],'game_title'].to_list()[0]
        date = games.loc[games['id'].astype(str)==query['game_id'][0],'date'].to_list()[0]
        all_strengths = ['3v3','3v4','3v5','4v3','4v4','4v5','4v6','5v3','5v4','5v5','5v6','6v4','6v5']
        #If filters is true among the url parameters then display the filters with the url params setting the values of the filters
        if query['filters'][0] == 'true':
            #Iterate through query and parse params with multiple selections
            for param in query.keys():
                q_string = query[param][0]
                query[param] = q_string.split(',')

            return ui.panel_well(
                ui.tags.div(
                {"class": "form-row"},
                    ui.input_date('game_date','Date',value=date),
                    ui.input_selectize('game_title','Game',{query['game_id'][0]:game_title}),
                    ui.input_selectize('event_type','Events',['blocked-shot','missed-shot','shot-on-goal','goal','hit','penalty','giveaway','takeaway','faceoff'],selected=query['event_type'],multiple=True),
                    ui.input_selectize('strength_state','Strengths',all_strengths,selected=(all_strengths if query['strength_state'][0]=='all' else query['strength_state']),multiple=True),
                ),
                ui.tags.div(
                {"class": "submit-button"},
                    ui.input_action_button('submit','Submit')
                )
            )
        else:
            return ui.input_action_button('submit','Submit',class_='hide')
    
    @reactive.effect
    @reactive.event(input.game_date)
    def update_games():
        query = active_params()
        if query['filters'][0] == 'true':
            games = schedule()

            date_games = games.loc[games['date']==str(input.game_date())].set_index('id')['game_title'].to_dict()
            ui.update_selectize(id='game_title',choices=date_games)

    @reactive.calc
    def params():
        query = active_params()
        
        #Set params based on filters
        if query['filters'][0] == 'true':
            query['game_id'] = [str(input.game_title())]
            query['event_type'] = [",".join(input.event_type())]
            query['strength_state'] = [",".join(input.strength_state())]

            return query
        else:
            return query
    
    submitted = reactive.Value(False)

    @reactive.Effect
    def startup():
        if not submitted.get():
            submitted.set(True)

    @output()
    @render_widget
    @reactive.event(input.submit, submitted)
    def plot_game():
        query = params()

        #Iterate through query and parse params with multiple selections
        for param in query.keys():
            q_string = query[param][0]
            query[param] = q_string.split(',')

        print(query)
        #Determine which season to load based on the input game_id
        front_year = int(query['game_id'][0][0:4])
        season = f'{front_year}{front_year+1}'
        #Load appropriate dataframe
        df = pd.read_parquet(f'https://f005.backblazeb2.com/file/weakside-breakout/pbp/{season}.parquet')
    
        #Prepare dataframe for plotting based on URL parameters
        df = df.loc[df['game_id'].astype(str).isin(query['game_id'])].replace({np.nan: None})
        df = wsba_plt.prep(df,events=query['event_type'],strengths=query['strength_state'])

        #Return empty rink if no data exists else continue
        if df.empty:
            return wsba_plt.wsba_rink()
        else:
            game_title = df['game_title'].to_list()[0]
            colors = wsba_plt.colors(df)
            rink = wsba_plt.wsba_rink()

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

            return rink.update_layout(
                title=dict(
                    text=game_title,
                    x=0.5, y=0.94,
                    xanchor='center',
                    yanchor='top',
                    font=dict(color='white')
                ),
                           
                legend=dict(
                    orientation='h',
                    x=0.49,
                    y=-0.04,
                    xanchor='center',
                    yanchor='bottom',
                    font=dict(color='white')
                ),

                hoverlabel=dict(
                    font_size=10
                )
            )

app = App(app_ui, server)