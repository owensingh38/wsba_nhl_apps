import pandas as pd
import numpy as np
import plotly.graph_objects as go
import matplotlib.pyplot as plt
import rink_plot
from scipy.interpolate import griddata
from scipy.ndimage import gaussian_filter

def wsba_rink(setting='full', vertical=False):
    return rink_plot.rink(setting=setting, vertical=vertical)

def player_events(df,skaters):
    df['onice'] = df['home_on_1_id'].astype(str) + ";" + df['home_on_2_id'].astype(str) + ";" + df['home_on_3_id'].astype(str) + ";" + df['home_on_4_id'].astype(str) + ";" + df['home_on_5_id'].astype(str) + ";" + df['home_on_6_id'].astype(str) + ";" + df['away_on_1_id'].astype(str) + ";" + df['away_on_2_id'].astype(str) + ";" + df['away_on_3_id'].astype(str) + ";" + df['away_on_4_id'].astype(str) + ";" + df['away_on_5_id'].astype(str) + ";" + df['away_on_6_id'].astype(str)

    if len(skaters)>2:
        mask = ((df['onice'].str.contains(skaters[0])) & (df['onice'].str.contains(skaters[1])) & (df['onice'].str.contains(skaters[2])))
    else:
        mask = ((df['onice'].str.contains(skaters[0])) & (df['onice'].str.contains(skaters[1])))

    return df[mask]

def heatmap(df,team,skaters,events,strengths,onice):
    df = df.copy()
    df = df.loc[df['event_type'].isin(['missed-shot','shot-on-goal','goal'])].replace({np.nan: None})

    df['event_team_abbr_2'] = np.where(df['home_team_abbr']==df['event_team_abbr'],df['away_team_abbr'],df['home_team_abbr'])
    df['strength_state_2'] = df['strength_state'].str[::-1]

    df = df.fillna(0)
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

    df['home_on_ice'] = df['home_on_1_id'].astype(str) + ";" + df['home_on_2_id'].astype(str) + ";" + df['home_on_3_id'].astype(str) + ";" + df['home_on_4_id'].astype(str) + ";" + df['home_on_5_id'].astype(str) + ";" + df['home_on_6_id'].astype(str)
    df['away_on_ice'] = df['away_on_1_id'].astype(str) + ";" + df['away_on_2_id'].astype(str) + ";" + df['away_on_3_id'].astype(str) + ";" + df['away_on_4_id'].astype(str) + ";" + df['away_on_5_id'].astype(str) + ";" + df['away_on_6_id'].astype(str)

    df['onice_for'] = np.where(df['home_team_abbr']==df['event_team_abbr'],df['home_on_ice'],df['away_on_ice'])
    df['onice_against'] = np.where(df['away_team_abbr']==df['event_team_abbr'],df['home_on_ice'],df['away_on_ice'])

    df['strength_state'] = np.where(df['strength_state'].isin(['5v5','5v4','4v5']),df['strength_state'],'Other')
    df['strength_state_2'] = np.where(df['strength_state_2'].isin(['5v5','5v4','4v5']),df['strength_state_2'],'Other')
        
    if strengths != 'all':
        if onice == 'against':
            df = df.loc[((df['strength_state_2'].isin(strengths)))]
        else:
            df = df.loc[((df['strength_state'].isin(strengths)))]

    [x,y] = np.round(np.meshgrid(np.linspace(x_min,x_max,(x_max-x_min)),np.linspace(-42.5,42.5,85)))
    xgoals = griddata((df['x'],df['y']),df['xG'],(x,y),method='cubic',fill_value=0)
    xgoals = np.where(xgoals < 0,0,xgoals)
    xgoals_smooth = gaussian_filter(xgoals,sigma=3)

    if len(skaters)>2:
        mask = ((df['onice'].str.contains(skaters[0])) & (df['onice'].str.contains(skaters[1])) & (df['onice'].str.contains(skaters[2])))
    else:
        mask = ((df['onice'].str.contains(skaters[0])) & (df['onice'].str.contains(skaters[1])))

    if onice == 'for':
        player_shots = df.loc[(df['event_team_abbr']==team)&mask]
    else:
        player_shots = df.loc[(df['event_team_abbr_2']==team)&mask]

    [x,y] = np.round(np.meshgrid(np.linspace(x_min,x_max,(x_max-x_min)),np.linspace(-42.5,42.5,85)))
    xgoals_player = griddata((player_shots['x'],player_shots['y']),player_shots['xG'],(x,y),method='cubic',fill_value=0)
    xgoals_player = np.where(xgoals_player < 0,0,xgoals_player)

    difference = (gaussian_filter(xgoals_player,sigma = 3)) - xgoals_smooth
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

    return player_shots, fig

def calc_team(pbp,game_strength):
    teams = []
    fenwick_events = ['missed-shot','shot-on-goal','goal']

    for team in [('away','home'),('home','away')]:
        #Flip strength state (when necessary) and filter by game strength if not "all"
        if game_strength != "all":
            if game_strength not in ['3v3','4v4','5v5']:
                for strength in game_strength:
                    pbp['strength_state'] = np.where(np.logical_and(pbp['event_team_venue']==team[1],pbp['strength_state']==strength[::-1]),strength,pbp['strength_state'])

            pbp = pbp.loc[pbp['strength_state'].isin(game_strength)]

        pbp['xGF'] = np.where(pbp['event_team_abbr'] == pbp[f'{team[0]}_team_abbr'], pbp['xG'], 0)
        pbp['xGA'] = np.where(pbp['event_team_abbr'] == pbp[f'{team[1]}_team_abbr'], pbp['xG'], 0)
        pbp['GF'] = np.where((pbp['event_type'] == "goal") & (pbp['event_team_abbr'] == pbp[f'{team[0]}_team_abbr']), 1, 0)
        pbp['GA'] = np.where((pbp['event_type'] == "goal") & (pbp['event_team_abbr'] == pbp[f'{team[1]}_team_abbr']), 1, 0)
        pbp['SF'] = np.where((pbp['event_type'].isin(['shot-on-goal','goal'])) & (pbp['event_team_abbr'] == pbp[f'{team[0]}_team_abbr']), 1, 0)
        pbp['SA'] = np.where((pbp['event_type'].isin(['shot-on-goal','goal'])) & (pbp['event_team_abbr'] == pbp[f'{team[1]}_team_abbr']), 1, 0)
        pbp['FF'] = np.where((pbp['event_type'].isin(fenwick_events)) & (pbp['event_team_abbr'] == pbp[f'{team[0]}_team_abbr']), 1, 0)
        pbp['FA'] = np.where((pbp['event_type'].isin(fenwick_events)) & (pbp['event_team_abbr'] == pbp[f'{team[1]}_team_abbr']), 1, 0)
        pbp['CF'] = np.where((pbp['event_type'].isin(fenwick_events+['blocked-shot'])) & (pbp['event_team_abbr'] == pbp[f'{team[0]}_team_abbr']), 1, 0)
        pbp['CA'] = np.where((pbp['event_type'].isin(fenwick_events+['blocked-shot'])) & (pbp['event_team_abbr'] == pbp[f'{team[1]}_team_abbr']), 1, 0)
        pbp['HF'] =  np.where((pbp['event_type']=='hit') & (pbp['event_team_abbr'] == pbp[f'{team[0]}_team_abbr']), 1, 0)
        pbp['HA'] = np.where((pbp['event_type']=='hit') & (pbp['event_team_abbr'] == pbp[f'{team[1]}_team_abbr']), 1, 0)
        pbp['Penl'] = np.where((pbp['event_type']=='penalty') & (pbp['event_team_abbr'] == pbp[f'{team[0]}_team_abbr']), 1, 0)
        pbp['Penl2'] = np.where((pbp['event_type']=='penalty') & (pbp['penalty_duration']==2) & (pbp['event_team_abbr'] == pbp[f'{team[0]}_team_abbr']), 1, 0)
        pbp['Penl5'] = np.where((pbp['event_type']=='penalty') & (pbp['penalty_duration']==5) & (pbp['event_team_abbr'] == pbp[f'{team[0]}_team_abbr']), 1, 0)
        pbp['PIM'] = np.where((pbp['event_team_abbr'] == pbp[f'{team[0]}_team_abbr']), pbp['penalty_duration'], 0)
        pbp['Draw'] = np.where((pbp['event_type']=='penalty') & (pbp['event_team_abbr'] == pbp[f'{team[1]}_team_abbr']), 1, 0)
        pbp['Give'] = np.where((pbp['event_type']=='giveaway') & (pbp['event_team_abbr'] == pbp[f'{team[0]}_team_abbr']), 1, 0)
        pbp['Take'] = np.where((pbp['event_type']=='takeaway') & (pbp['event_team_abbr'] == pbp[f'{team[0]}_team_abbr']), 1, 0)
        pbp['Block'] = pbp['CA'] - pbp['FA']
        pbp['RushF'] = np.where((pbp['event_team_abbr'] == pbp[f'{team[0]}_team_abbr'])&(pbp['rush']>0), 1, 0)
        pbp['RushA'] = np.where((pbp['event_team_abbr'] == pbp[f'{team[1]}_team_abbr'])&(pbp['rush']>0), 1, 0)
        pbp['RushFxG'] = np.where((pbp['event_team_abbr'] == pbp[f'{team[0]}_team_abbr'])&(pbp['rush']>0), pbp['xG'], 0)
        pbp['RushAxG'] = np.where((pbp['event_team_abbr'] == pbp[f'{team[1]}_team_abbr'])&(pbp['rush']>0), pbp['xG'], 0)
        pbp['RushFG'] = np.where((pbp['event_type'] == "goal") & (pbp['event_team_abbr'] == pbp[f'{team[0]}_team_abbr'])&(pbp['rush']>0), 1, 0)
        pbp['RushAG'] = np.where((pbp['event_type'] == "goal") & (pbp['event_team_abbr'] == pbp[f'{team[1]}_team_abbr'])&(pbp['rush']>0), 1, 0)

        stats = pbp.groupby([f'{team[0]}_team_abbr','season']).agg(
            GP=('game_id','nunique'),
            TOI=('event_length','sum'),
            FF=('FF', 'sum'),
            FA=('FA', 'sum'),
            GF=('GF', 'sum'),
            GA=('GA', 'sum'),
            SF=('SF','sum'),
            SA=('SA','sum'),
            xGF=('xGF', 'sum'),
            xGA=('xGA', 'sum'),
            CF=('CF','sum'),
            CA=('CA','sum'),
            HF=('HF','sum'),
            HA=('HA','sum'),
            Penl=('Penl','sum'),
            Penl2=('Penl2','sum'),
            Penl5=('Penl5','sum'),
            PIM=('PIM','sum'),
            Draw=('Draw','sum'),
            Give=('Give','sum'),
            Take=('Take','sum'),
            Block=('Block','sum'),
            RushF=('RushF','sum'),
            RushA=('RushA','sum'),
            RushFxG=('RushFxG','sum'),
            RushAxG=('RushAxG','sum'),
            RushFG=('RushFG','sum'),
            RushAG=('RushAG','sum'),
        ).reset_index().rename(columns={f'{team[0]}_team_abbr':"Team",'season':"Season",'game_id':'Game'})
        teams.append(stats)
    
    onice_stats = pd.concat(teams).groupby(['Team','Season']).agg(
            GP=('GP','sum'),
            TOI=('TOI','sum'),
            FF=('FF', 'sum'),
            FA=('FA', 'sum'),
            GF=('GF', 'sum'),
            GA=('GA', 'sum'),
            SF=('SF','sum'),
            SA=('SA','sum'),
            xGF=('xGF', 'sum'),
            xGA=('xGA', 'sum'),
            CF=('CF','sum'),
            CA=('CA','sum'),
            HF=('HF','sum'),
            HA=('HA','sum'),
            Penl=('Penl','sum'),
            Penl2=('Penl2','sum'),
            Penl5=('Penl5','sum'),
            PIM=('PIM','sum'),
            Draw=('Draw','sum'),
            Give=('Give','sum'),
            Take=('Take','sum'),
            Block=('Block','sum'),
            RushF=('RushF','sum'),
            RushA=('RushA','sum'),
            RushFxG=('RushFxG','sum'),
            RushAxG=('RushAxG','sum'),
            RushFG=('RushFG','sum'),
            RushAG=('RushAG','sum'),
    ).reset_index()

    for col in onice_stats.columns.to_list()[2:30]:
        onice_stats[col] = onice_stats[col].astype(float)

    onice_stats['ShF%'] = onice_stats['GF']/onice_stats['SF']
    onice_stats['xGF/FF'] = onice_stats['xGF']/onice_stats['FF']
    onice_stats['GF/xGF'] = onice_stats['GF']/onice_stats['xGF']
    onice_stats['FshF%'] = onice_stats['GF']/onice_stats['FF']
    onice_stats['ShA%'] = onice_stats['GA']/onice_stats['SA']
    onice_stats['xGA/FA'] = onice_stats['xGA']/onice_stats['FA']
    onice_stats['GA/xGA'] = onice_stats['GA']/onice_stats['xGA']
    onice_stats['FshA%'] = onice_stats['GA']/onice_stats['FA']
    onice_stats['PM%'] = onice_stats['Take']/(onice_stats['Give']+onice_stats['Take'])
    onice_stats['HF%'] = onice_stats['HF']/(onice_stats['HF']+onice_stats['HA'])
    onice_stats['PENL%'] = onice_stats['Draw']/(onice_stats['Draw']+onice_stats['Penl'])
    onice_stats['GSAx'] = onice_stats['xGA']/onice_stats['GA']

    return onice_stats


def calculate_stats(pbp,team,game_strength):
    per_sixty = ['Fi','xGi','Gi','A1','A2','P1','P','Si','OZF','NZF','DZF','FF','FA','xGF','xGA','GF','GA','SF','SA','CF','CA','HF','HA','Give','Take','Penl','Penl2','Penl5','Draw','Block']

    complete = calc_team(pbp,game_strength)

    #WSBA
    complete['WSBA'] = complete['Team']+complete['Season'].astype(str)

    #Set TOI to minute
    complete['TOI'] = complete['TOI']/60

    #Add per 60 stats
    for stat in per_sixty[11:len(per_sixty)]:
        complete[f'{stat}/60'] = (complete[stat]/complete['TOI'])*60
        
    complete['GF%'] = complete['GF']/(complete['GF']+complete['GA'])
    complete['SF%'] = complete['SF']/(complete['SF']+complete['SA'])
    complete['xGF%'] = complete['xGF']/(complete['xGF']+complete['xGA'])
    complete['FF%'] = complete['FF']/(complete['FF']+complete['FA'])
    complete['CF%'] = complete['CF']/(complete['CF']+complete['CA'])

    head = ['Team','Game'] if 'Game' in complete.columns else ['Team']
    complete = complete[head+[
        'Season','WSBA',
        'GP','TOI',
        "GF","SF","FF","xGF","xGF/FF","GF/xGF","ShF%","FshF%",
        "GA","SA","FA","xGA","xGA/FA","GA/xGA","ShA%","FshA%",
        'CF','CA',
        'GF%','SF%','FF%','xGF%','CF%',
        'HF','HA','HF%',
        'Penl','Penl2','Penl5','PIM','Draw','PENL%',
        'Give','Take','PM%',
        'Block',
        'RushF','RushA','RushFxG','RushAxG','RushFG','RushAG',
        'GSAx'
    ]+[f'{stat}/60' for stat in per_sixty[11:len(per_sixty)]]]

    return complete.loc[complete['Team']==team]