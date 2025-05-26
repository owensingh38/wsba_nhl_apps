import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import rink_plot
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter

def wsba_rink(setting='full', vertical=False):
    return rink_plot.rink(setting=setting, vertical=vertical)

def heatmap(df,skater,team,events,strengths,onice):
    df['event_team_abbr_2'] = np.where(df['home_team_abbr']==df['event_team_abbr'],df['away_team_abbr'],df['home_team_abbr'])

    df = df.loc[(df['event_type'].isin(events))&(df['x_adj'].notna())&(df['y_adj'].notna())]
    if onice == 'for':
        df['x'] = abs(df['x_adj'])
        df['y'] = np.where(df['x_adj']<0,-df['y_adj'],df['y_adj'])
        df['event_distance'] = abs(df['event_distance'].fillna(0))
        df = df.loc[(df['event_distance']<=89)&(df['x']<=89)&(df['empty_net']==0)]

        x_min = 0
        x_max = 100
    else:
        df['x'] = -abs(df['x_adj'])
        df['y'] = np.where(df['x_adj']>0,-df['y_adj'],df['y_adj'])
        df['event_distance'] = -abs(df['event_distance'])
        df = df.loc[(df['event_distance']>-89)&(df['x']>-89)&(df['empty_net']==0)]

        x_min = -100
        x_max = 0

    df = df.loc[(abs(df['event_distance'].fillna(0))<=89)&(abs(df['x'])<=89)&(df['empty_net']==0)]
    df['home_on_ice'] = df['home_on_1_id'].astype(str) + ";" + df['home_on_2_id'].astype(str) + ";" + df['home_on_3_id'].astype(str) + ";" + df['home_on_4_id'].astype(str) + ";" + df['home_on_5_id'].astype(str) + ";" + df['home_on_6_id'].astype(str)
    df['away_on_ice'] = df['away_on_1_id'].astype(str) + ";" + df['away_on_2_id'].astype(str) + ";" + df['away_on_3_id'].astype(str) + ";" + df['away_on_4_id'].astype(str) + ";" + df['away_on_5_id'].astype(str) + ";" + df['away_on_6_id'].astype(str)

    df['onice_for'] = np.where(df['home_team_abbr']==df['event_team_abbr'],df['home_on_ice'],df['away_on_ice'])
    df['onice_against'] = np.where(df['away_team_abbr']==df['event_team_abbr'],df['home_on_ice'],df['away_on_ice'])

    df['strength_state'] = np.where(df['strength_state'].isin(['5v5','5v4','4v5']),df['strength_state'],'Other')
        
    if strengths != 'all':
        df = df.loc[((df['strength_state'].isin(strengths)))]

    [x,y] = np.round(np.meshgrid(np.linspace(x_min,x_max,(x_max-x_min)),np.linspace(-42.5,42.5,85)))
    xgoals = griddata((df['x'],df['y']),df['xG'],(x,y),method='cubic',fill_value=0)
    xgoals = np.where(xgoals < 0,0,xgoals)
    xgoals_smooth = gaussian_filter(xgoals,sigma=3)

    if onice == 'for':
        player_shots = df.loc[(df['onice_for'].str.contains(skater))&(df['event_team_abbr']==team)]
    else:
        player_shots = df.loc[(df['onice_against'].str.contains(skater))&(df['event_team_abbr_2']==team)]

    [x,y] = np.round(np.meshgrid(np.linspace(x_min,x_max,(x_max-x_min)),np.linspace(-42.5,42.5,85)))
    xgoals_player = griddata((player_shots['x'],player_shots['y']),player_shots['xG'],(x,y),method='cubic',fill_value=0)
    xgoals_player = np.where(xgoals_player < 0,0,xgoals_player)
    
    difference = (gaussian_filter(xgoals_player,sigma = 3)) - xgoals_smooth

    fig = go.Figure(
        data = go.Heatmap(x=np.linspace(x_min,x_max,(x_max-x_min)),
                            y=np.linspace(-42.5,42.5,85),
                            z=difference,
                            colorscale=[[0.0,'red'],[0.5,'white'],[1.0,'blue']],
                            connectgaps=True,
                            zsmooth='best',
                            showscale=False)
    )

    return fig