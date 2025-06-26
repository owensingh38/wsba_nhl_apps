import pandas as pd
import numpy as np
import matplotlib.pyplot as plt
import plotly.graph_objects as go
import rink_plot

event_markers = {
    'faceoff':'X',
    'hit':'P',
    'blocked-shot':'v',
    'missed-shot':'o',
    'shot-on-goal':'D',
    'goal':'*',
    'giveaway':'1',
    'takeaway':'2',
    'penalty':''
    }  

def wsba_rink(setting='full', vertical=False):
    return rink_plot.rink(setting=setting, vertical=vertical)

def colors(df):
    team = list(df['event_team_abbr'])[0]
    season = list(df['season'])[0]
    team_data = pd.read_csv('https://f005.backblazeb2.com/file/weakside-breakout/info/nhl_teaminfo.csv')

    team_info ={
        team: list(team_data.loc[team_data['WSBA']==f'{team}{season}','Primary Color'])[0],
    }

    return team_info

def prep(df,events,strengths):
    df = df.loc[(df['event_type'].isin(events))]

    df['strength_state'] = np.where(df['strength_state'].isin(['5v5','5v4','4v5']),df['strength_state'],'Other')
    if strengths != 'all':
        df = df.loc[((df['strength_state'].isin(strengths)))]

    df['xG'] = df['xG'].fillna(0)
    df['size'] = np.where(df['xG']<=0,40,df['xG']*400)
    
    df['marker'] = df['event_type'].replace(event_markers)
    
    df['Description'] = df['description']
    df['Team'] = df['event_team_abbr']
    df['Event Num.'] = df['event_num']
    df['Period'] = df['period']
    df['Time (in seconds)'] = df['seconds_elapsed']
    df['Strength'] = df['strength_state']
    df['Away Score'] = df['away_score']
    df['Home Score'] = df['home_score']
    df['x'] = np.where(df['x_adj']<0,-df['y_adj'],df['y_adj'])
    df['y'] = abs(df['x_adj'])
    df['Event Distance from Attacking Net'] = df['event_distance']
    df['Event Angle to Attacking Net'] = df['event_angle']
    df['xG'] = df['xG']*100
    return df