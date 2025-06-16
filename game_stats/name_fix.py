import requests as rs
import pandas as pd
import numpy as np

def scrape_info(player_ids):
    #Given player id, return player information
    infos = []
    for player_id in player_ids:
        player_id = int(player_id)
        api = f'https://api-web.nhle.com/v1/player/{player_id}/landing'

        data = pd.json_normalize(rs.get(api).json())

        #Add name column
        data['fullName'] = (data['firstName.default'] + " " + data['lastName.default']).str.upper()

        #Append
        infos.append(data)

    df = pd.concat(infos)
    #Return: player data
    return df

def fix_names(stats,name='Player'):
    missing = stats.loc[stats[name]=='0']
    stats = stats.loc[stats[name]!='0']  
    
    if not missing.empty:
        data = scrape_info(missing['ID'])[['fullName','playerId','position','shootsCatches']].rename(columns={
            'playerId':'ID',
            'fullName':'Player',
            'position':'Position',
            'headshot':'Headshot',
            'heightInInches':'Height (in)',
            'weightInPounds':'Weight (lbs)',
            'birthDate':'Birthday',
            'birthCountry':'Nationality',
            'shootsCatches':'Handedness'}) 

        missing = missing.drop(columns=[name,'Position','Handedness'])         
        miss = pd.merge(missing,data,how='left',on=['ID'])

        df = pd.concat([stats,miss]).sort_values([name,'ID'])

        return df
    else:
        return stats