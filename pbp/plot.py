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

def wsba_rink():
    return rink_plot.rink(setting='full', vertical=False)

def colors(df):
    away_abbr = list(df['away_team_abbr'])[0]
    home_abbr = list(df['home_team_abbr'])[0]
    season = list(df['season'])[0]
    team_data = pd.read_csv('https://weakside-breakout.s3.us-east-2.amazonaws.com/info/nhl_teaminfo.csv')

    team_info ={
        away_abbr: list(team_data.loc[team_data['WSBA']==f'{away_abbr}{season}','Primary Color'])[0],
        home_abbr: list(team_data.loc[team_data['WSBA']==f'{home_abbr}{season}','Primary Color'])[0],
    }

    return team_info

def convert_time(seconds,period):
    period_seconds = seconds - ((period-1)*1200)
    minutes = int(period_seconds/60)
    seconds = int(((period_seconds/60)-minutes)*60)

    return f'{minutes}:{seconds:02}'

def prep(df,events,strengths):
    df = df.loc[(df['event_type'].isin(events))]

    df['strength_state'] = np.where(df['strength_state'].isin(['5v5','5v4','4v5']),df['strength_state'],'Other')
    if 'all' not in strengths:
        df = df.loc[((df['strength_state'].isin(strengths)))]

    df['xG'] = df['xG'].fillna(0)
    df['size'] = np.where(df['xG']<=0,40,df['xG']*400)
    
    df['marker'] = df['event_type'].replace(event_markers)

    df['Description'] = df['description']
    df['Team'] = df['event_team_abbr']
    df['Event Num.'] = df['event_num']
    df['Period'] = df['period']
    df['Time (in seconds)'] = df['seconds_elapsed']
    df['Time (in Period)'] = df.apply(lambda x: convert_time(x['Time (in seconds)'],x['Period']), axis=1)
    df['Strength'] = df['strength_state']
    df['Away Score'] = df['away_score']
    df['Home Score'] = df['home_score']
    df['x'] = df['x_adj']
    df['y'] = df['y_adj']
    df['Event Distance from Attacking Net'] = df['event_distance']
    df['Event Angle to Attacking Net'] = df['event_angle']
    return df

def timelines(df):
    df['Goals'] = np.where(df['event_type']=='goal',1,0)
    df['Shots'] = np.where(df['event_type'].isin(['shot-on-goal','goal']),1,0)
    df['Fenwick'] = np.where(df['event_type'].isin(['missed-shot','shot-on-goal','goal']),1,0)

    df['xG'] = df.groupby('event_team_abbr')['xG'].cumsum()
    df['Goals'] = df.groupby('event_team_abbr')['Goals'].cumsum()
    df['Shots'] = df.groupby('event_team_abbr')['Shots'].cumsum()
    df['Fenwick'] = df.groupby('event_team_abbr')['Fenwick'].cumsum()
    
    return df