import requests
import pandas as pd
from pandas import json_normalize 
from datetime import datetime
from time import sleep
import json
import pytz

def call_nhl(startSeason, endSeason=None):

  # Possible to call API for multiple seasons, 
  # but if no end season is provided, set end season = start season.
  if not endSeason:
    endSeason = startSeason

  # Headers in the API call authenticate the requests
  headers = {
      'authority': 'api.nhle.com',
      # Could cycle through different user agents using the fake-useragent module 
      # if the API appears to be blocking repeated calls
      'user-agent': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/87.0.4280.141 Safari/537.36',
      'accept': '*/*',
      'origin': 'http://www.nhl.com',
      'sec-fetch-site': 'cross-site',
      'sec-fetch-mode': 'cors',
      'sec-fetch-dest': 'empty',
      'referer': 'http://www.nhl.com/',
      'accept-language': 'en-US,en;q=0.9',
  }

  params = (
      ('isAggregate', 'false'),
      ('isGame', 'true'),
      ('sort', '[{"property":"gameDate","direction":"DESC"}]'),
      ('start', '0'),
      # Setting limit = 0 returns all games for given season
      ('limit', '0'),
      ('factCayenneExp', 'gamesPlayed>=1'),
      # Through trial and error, gameTypeId=2 corresponds to regular season games
      # The f-string inserts endSeason and startSeason into the parameters
      ('cayenneExp', f'gameTypeId=2 and seasonId<={endSeason} and seasonId>={startSeason}'),
  )
  
  # Call API with given headers and parameters
  response = requests.get('https://api.nhle.com/stats/rest/en/team/summary', headers=headers, params=params)

  return response

def get_gameData(startYear, numSeasons):

  seasons = [f"{startYear+i}{startYear+i+1}" for i in range(numSeasons)]

  rows=0
  res = {}

  for s in seasons:
    response = call_nhl(s)

    # Try except is probably more appropriate,
    # but if it ain't broke...
    if response:
      response = response.json()
      rows+=len(response['data'])
      df = pd.json_normalize(response['data'])
      res[s] = df
      print(f"Number of games grabbed for {s} = {len(response['data'])}. Total = {rows}")
    else:
      print("ERROR: unable to connect to NHL API")
      return None

  return res

def get_teamLU(df):
  return dict(zip(df['teamId'], df['teamFullName']))

def home_road(df, teamLU):
  res = {}
  res['home'] = df[df['homeRoad']=='H']['teamId'].values[0]
  res['road'] = df[df['homeRoad']=='R']['teamId'].values[0]

  res['homeName'] = teamLU[res['home']]
  res['roadName'] = teamLU[res['road']]

  return pd.Series(res, index=res.keys())

# def get_schedule(df, teamLU):
#   return df.groupby(['gameId', 'gameDate']).apply(home_road, teamLU)

def get_schedule(season_start = None):
  if season_start == None:
    if datetime.now().month < 10:
      season_start = datetime.now().year - 1
    else:
      season_start = datetime.now().year

  headers = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:78.0) Gecko/20100101 Firefox/78.0',
    'Accept': '*/*',
    'Accept-Language': 'en-CA,en-US;q=0.7,en;q=0.3',
    'Origin': 'https://www.nhl.com',
    'DNT': '1',
    'Connection': 'keep-alive',
    'Referer': 'https://www.nhl.com/',
  }

  params = (
      #('startDate', f'{season_start}-10-1'),
      #('endDate', f'{season_start+1}-05-15'),
      ('season', f'{season_start}{season_start+1}'),
      ('hydrate', 'team,linescore'),
      ('site', 'en_nhlCA'),
      ('teamId', ''),
      ('gameType', 'R'),
      ('timecode', ''),
  )

  response = requests.get('https://statsapi.web.nhl.com/api/v1/schedule', headers=headers, params=params)
  
  data = json.loads(response.text)
  df = pd.json_normalize(data['dates'], record_path = ['games'])
  
  eastern = pytz.timezone('US/Eastern')

  sched_df = df.loc[:,[
             'gameDate', 
             'teams.home.team.abbreviation', 
             'teams.away.team.abbreviation',
             'teams.home.score',
             'teams.away.score'
           ]]


  sched_df['gameDate'] = (pd.to_datetime(sched_df['gameDate'])
                            .dt.tz_convert(eastern)
                            .dt.strftime('%Y%m%d'))
  sched_df.columns = ['gameDate', 'homeTeam', 'awayTeam', 'homeScore', 'awayScore']
  
  return sched_df
