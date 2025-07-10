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
    ui.output_ui('add_filters'),
    output_widget("plot_game"),
    ui.output_ui('metrics'),
    ui.output_ui('timeline_filter'),
    ui.output_data_frame("plays"),
    output_widget("timelines"),
)

def server(input, output, session):
    query = reactive.Value(None)

    def schedule():
        schedule = pd.read_csv('https://weakside-breakout.s3.us-east-2.amazonaws.com/info/schedule.csv')
        
        return schedule.loc[schedule['gameState'].isin(['OFF','FINAL'])]

    @reactive.Effect
    def query_params():
        #Retreive query parameters
        search = session.input[".clientdata_url_search"]()
        q = parse_qs(urlparse(search).query)

        print(q)
        #If no input data is provided automatically provide a select game and plot all 5v5 fenwick shots
        defaults = {
            'game_id':[str(schedule()['id'].iloc[-1])],
            'event_type':['missed-shot,shot-on-goal,goal'],
            'strength_state':['all'],
            'filters':['false'],
            'table':['false'],
            'title':['true']
        }

        for key in defaults.keys():
            if key not in q.keys():
                q.update({key:defaults[key]})
        
        query.set(q)
        
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
                {"class": "form-row custom-input"},
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

    game_df = reactive.Value(pd.DataFrame())
    show_table = reactive.Value(False)
    @reactive.effect
    @reactive.event(input.submit, submitted)
    def ret_game():
        query = params()

        #Iterate through query and parse params with multiple selections
        #If it is already parsed skip this
        for param in query.keys():
            if len(query[param])>1:
                ''
            else:
                q_string = query[param][0]
                query[param] = q_string.split(',')

        print(query)
        #Determine which season to load based on the input game_id
        front_year = int(query['game_id'][0][0:4])
        season = f'{front_year}{front_year+1}'
        #Load appropriate dataframe
        df = pd.read_parquet(f'https://weakside-breakout.s3.us-east-2.amazonaws.com/pbp/{season}.parquet')

        #Prepare dataframe for plotting based on URL parameters
        game_data = df.loc[df['game_id'].astype(str).isin(query['game_id'])].replace({np.nan: None})
        game_data = wsba_plt.prep(game_data,events=query['event_type'],strengths=query['strength_state'])

        game_df.set(game_data)

        if query['table'][0]=='true':
            show_table.set(True)
    
    @output()
    @render_widget
    @reactive.event(input.submit, submitted)
    def plot_game():
        #Retreive game
        df = game_df.get().copy()

        #Return empty rink if no data exists else continue
        if df.empty:
            return wsba_plt.wsba_rink()
        else:
            game_title = df['game_title'].to_list()[0]
            print(game_title)
            colors = wsba_plt.colors(df)
            rink = wsba_plt.wsba_rink()

            plot = px.scatter(df,
                              x='x', y='y',
                              size='size',
                              color='Team',
                              color_discrete_map=colors,
                              hover_name='Description',
                              hover_data=['Event Num.', 'Period', 'Time (in Period)',
                                          'Strength',
                                          'Away Score', 'Home Score', 'x', 'y',
                                          'Event Distance from Attacking Net',
                                          'Event Angle to Attacking Net',
                                          'xG'])

            for trace in plot.data:
                rink.add_trace(trace)

            if active_params()['title'][0]=='false':
                return rink.update_layout(                                
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
            else:
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

    @output
    @render.ui
    def metrics():
        query = params()
        if query['table'][0]=='true':
            return ui.tags.div(
                    {'class':'custom-input'},
                    ui.input_selectize('metric_select','Metric',['Plays','Timelines'])
                )
        else:
            return None
        
    @output
    @render.ui
    @reactive.event(input.metric_select)
    def timeline_filter():
        if input.metric_select()=='Timelines':
            return ui.tags.div(
                    {'class':'custom-input'},
                    ui.input_selectize('timeline_select','Timeline',['xG','Fenwick','Shots','Goals'])
                )
        else:
            return None

    @output()
    @render.data_frame
    @reactive.event(input.submit,input.metric_select)
    def plays():
        if not show_table.get():
            return None
        else:
            if input.metric_select()=='Timelines':
                return None
            else:
                df = game_df.get().copy()[['event_num','period','Time (in Period)','strength_state','event_type','Description','event_team_abbr','event_player_1_name','shot_type','zone_code','x','y','away_score','home_score','xG']].rename(columns={
                    'event_num':'#',
                    'period':'Period',
                    'strength_state':'Strength State',
                    'event_type':'Event',
                    'event_team_abbr':'Team',
                    'event_player_1_name':'Player',
                    'shot_type':'Shot Type',
                    'zone_code':'Zone Code',
                    'away_score':'Away Score',
                    'home_score':'Home Score'
                })
                
                df['xG'] = df['xG'].round(4)
                return render.DataTable(df)

    @output()
    @render_widget
    @reactive.event(input.submit,input.metric_select,input.timeline_select)
    def timelines():
        if not show_table.get():
            return None
        else:
            if input.metric_select()=='Plays':
                return None
            else:
                data = wsba_plt.timelines(game_df.get().copy())
                colors = wsba_plt.colors(data)
                timelines = px.line(data,
                                    x='Time (in Period)',
                                    y=input.timeline_select(),
                                    color='Team',
                                    color_discrete_map=colors,
                                    hover_data=['Away Score','Home Score']
                                    )

                timelines.update_traces(
                    line=dict(
                        width=4
                    ))

                return timelines.update_layout(  
                    paper_bgcolor="rgba(0,0,0,0)", 
                    plot_bgcolor="rgba(0,0,0,0)",  
                    font_color='white',         
                    xaxis=dict(title=dict(text='Time (in Period)'),showgrid=False),
                    yaxis=dict(title=dict(text=input.timeline_select()),showgrid=False),

                    legend=dict(
                        title='Team',
                        orientation='h',
                        x=0.5,
                        y=1,
                        xanchor='center',
                        yanchor='top',
                        font=dict(color='white')
                    ),

                    hoverlabel=dict(
                        font_size=10
                    )
            )

app = App(app_ui, server)