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
    team_data = pd.read_csv('https://f005.backblazeb2.com/file/weakside-breakout/info/nhl_teaminfo.csv')

    team_info ={
        away_abbr: list(team_data.loc[team_data['WSBA']==f'{away_abbr}{season}','Primary Color'])[0],
        home_abbr: list(team_data.loc[team_data['WSBA']==f'{home_abbr}{season}','Primary Color'])[0],
    }

    return team_info

def prep(df,events,strengths):
    df = df.loc[(df['event_type'].isin(events))]
    
    if 'all' not in strengths:
        df = df.loc[((df['strength_state'].isin(strengths)))]

    df['xG'] = df['xG'].fillna(0)
    df['size'] = np.where(df['xG']<=0,40,df['xG']*400)
    
    df['marker'] = df['event_type'].replace(event_markers)

    info = pd.read_csv('https://f005.backblazeb2.com/file/weakside-breakout/info/nhl_teaminfo.csv')
    df = pd.merge(df,info,how='left',left_on=['season','event_team_abbr'],right_on=['seasonId','triCode'])

    df['Description'] = df['description']
    df['Logo'] = '<img src="'+df['teamLogo']+'" width="100%" height="30px">'
    df['Team'] = df['event_team_abbr']
    df['Event Num.'] = df['event_num']
    df['Period'] = df['period']
    df['Time (in seconds)'] = df['seconds_elapsed']
    df['Strength'] = df['strength_state']
    df['Away Score'] = df['away_score']
    df['Home Score'] = df['home_score']
    df['x'] = df['x_adj']
    df['y'] = df['y_adj']
    df['Event Distance from Attacking Net'] = df['event_distance']
    df['Event Angle to Attacking Net'] = df['event_angle']
    df['xG'] = df['xG']*100
    return df

def timelines(df):
    df['xG'] = (df['xG']/100).replace({np.nan:0}).astype(float)
    df['Goals'] = np.where(df['event_type']=='goal',1,0)
    df['Shots'] = np.where(df['event_type'].isin(['shot-on-goal','goal']),1,0)
    df['Fenwick'] = np.where(df['event_type'].isin(['missed-shot','shot-on-goal','goal']),1,0)

    df['xG'] = df.groupby('event_team_abbr')['xG'].cumsum()
    df['Goals'] = df.groupby('event_team_abbr')['Goals'].cumsum()
    df['Shots'] = df.groupby('event_team_abbr')['Shots'].cumsum()
    df['Fenwick'] = df.groupby('event_team_abbr')['Fenwick'].cumsum()
    
    return df