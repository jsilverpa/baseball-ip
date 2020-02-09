# %%
"""
Introduction

Imagining an all-time, all-star team often means selecting the greatest players by using advanced metrics like WARP (Wins Above Replacement Player) to measure players’ values. But mathematical and algorithmic techniques allow us to take this exercise to a whole new level.    We can add extra conditions to our player selections and see the game in a whole new light.  What if we require that the team includes at least one player born in each of the major baseball-playing countries?    Or we dictate that there is an equal number of players from the National and American Leagues?  Or we pick modern players and dictate their maximum combined salary or maximum average age?  The possibilities are endless.

In this article, we pick an all-star team with a twist.   We set out to determine the greatest team ever, comprised of the most exceptional players that have played the game.  We decided to make this team representative of baseball’s history, so we picked a team that has exactly one player in each of the ten positions (eight fielders plus a LHP and RHP), and then added a condition that our team must consist of exactly one player from each of the last 10 decades.

In the text below, we’ll introduce a powerful technique called integer programming.  Integer programming allows for creating different conditions and provides corresponding solutions that satisfy the conditions. We’ll use this technique to select our all-star team of the ten best players, each from a different decade.  And finally, we’ll point you to code that will allow you to examine the data, run your own analyses, and experiment with picking a team subject to your own conditions.


"""

# %%
"""

"""

# %%
"""
First, let's define some utility functions for sorting and displaying player statistics.
"""

# %%
import numpy as np
import cvxpy as cp
import pandas as pd
import json

import pdb
import team_map
MIN_DECADE = 1920
MAX_DECADE = 2010
DATA_DIR = "/Users/jsilver/integer/baseball_ip/kaggle/input/baseball-ip/"
pd.options.display.width = 120
 
batter_header = ['Id','Name',  'Dec', 'Pos', 'WARP', 'BA', 'OBP', 'SLG', 'H', 'HR', 'RBI', 'R', 'AB']
pitcher_header = ['Id', 'Name', 'Dec', 'Pos', 'WARP', 'Record', 'ERA', 'WHIP', 'K', 'IP']

def get_team(team, is_pitcher):
    team_table = []
    for iter, player in team.iterrows():
        player_row = [player.NAME, round(player.YEAR), player.POS, "{:.1f}".format(player.WARP)]
        if (is_pitcher):
            record =str(round(player.W)) + "-" + str(round(player.L))
            era = "{:.2f}".format(round(player.ER/player.IP * 9, 2))
            whip = "{:.3f}".format(round((player.BB + player.H)/player.IP, 3))
            player_row.extend([record, era, whip, round(player.SO), round(player.IP)])
            player_row.insert(0, round(player.PITCHER,0))
        else:
            ba = "{:.3f}".format(round(player.H/player.AB,3))
            obp = "{:.3f}".format(round((player.H+player.BB+player.HBP)/(player.AB+player.BB+player.HBP+0),3))
            slg = "{:.3f}".format(round(player.TB/player.AB,3))
            player_row.extend([ba, obp, slg,  round(player.H), round(player.HR), round(player.RBI), round(player.R), round(player.AB)])
            player_row.insert(0, round(player.BATTER,0))
        team_table.append(player_row)

    if (is_pitcher):
        team_table = pd.DataFrame(team_table, columns = pitcher_header)
    else:
        team_table = pd.DataFrame(team_table, columns = batter_header)
    return team_table

field_pos = ['C', '1B', '2B', '3B', 'SS', 'OF']
pitcher_pos = ['RHP', 'LHP']

def get_solution(ar, df):
    count = -1 
    picked_pitchers = pd.DataFrame()
    picked_batters = pd.DataFrame() 
    for x in np.nditer(ar):
        count = count + 1
        if (np.abs(x)  < 0.01):
            continue
        player = df.iloc[count]
        if (player.POS in pitcher_pos):
            picked_pitchers = picked_pitchers.append(player)
        else:
            picked_batters = picked_batters.append(player)
    picked_pitchers = picked_pitchers.sort_values(by = 'YEAR', ascending = True)
    picked_batters = picked_batters.sort_values(by = 'YEAR', ascending = True)
    return [get_team(picked_batters, False), get_team(picked_pitchers, True)]


def print_top_players(positions, min_year = 1920, count = 10 ):
    for pos in positions:
        pos_df = pd.read_csv(DATA_DIR + pos + ".csv")
        pos_df['POS'] = pos
        pos_df = pos_df.loc[pos_df.YEAR >= min_year]
        pos_df = pos_df.sort_values(by="WARP", ascending = False)
        is_pitcher = pos in pitcher_pos
        print(get_team(pos_df.head(count), is_pitcher))

# %%
"""
Let's explore the data to see who the top players are at each position over the various decades.
"""

# %%
#explore the data    
print_top_players(field_pos + pitcher_pos)


# %%
"""
Now let's create the constraints and the optimization function.
"""

# %%
def solve_ip(min_decade = MIN_DECADE, max_decade = MAX_DECADE, min_players_per_decade = 0, max_players_per_decade = 1, players_per_position = 1,
             team = []):
    #initialize a dictionary of vectors to hold the position constraints
    pos_list = {pos: [] for pos in field_pos + pitcher_pos}

    #initialize a dictionary of vectors to hold the decade constraints
    decade_vec = {decade: []  for decade in range(min_decade, max_decade+1, 10)}


    WAR_vec = []
    all_df = pd.DataFrame()

    #loop through each position
    for pos in field_pos + pitcher_pos:
        df = pd.read_csv(DATA_DIR + pos + ".csv")

        #remove players from decades too earlier than our first
        df = df.loc[df['YEAR'] >= min_decade]

	#remove players from decades 
        df = df.loc[df['YEAR'] <= max_decade]

        if (len(team) > 0):
            df = df.loc[df['TEAM'].isin(team)]

        #create pos column on dataframe for easy printing
        df['POS'] = pos

        #create an overall dataframe
        all_df = all_df.append(df, sort=False)
        zeroes = np.zeros(len(df))
        ones = np.ones(len(df))

        #set the position vector
        for pos_list_item in field_pos + pitcher_pos:
            if (pos == pos_list_item):
                pos_list[pos_list_item].extend(ones)
            else:
                pos_list[pos_list_item].extend(zeroes)

        #set the decade vectors
        for decade in range(min_decade, max_decade + 1, 10):
            this_decade = np.where(df['YEAR'] == decade, 1, 0)
            decade_vec[decade].extend(this_decade)

        #create a vector WAR values
        WAR_vec.extend(df['WARP'].to_list())
            


    selection = cp.Variable(len(WAR_vec), boolean = True)
    constraints = [(decade_vec[i] * selection <= max_players_per_decade) for i in range(min_decade, max_decade + 1, 10)] +  [(decade_vec[i] * selection >= min_players_per_decade) for i in range(min_decade, max_decade + 1, 10)]
    for pos in field_pos + pitcher_pos:
        max_players = players_per_position
        if (pos == 'OF'):
            max_players = 3 * players_per_position
        constraints.append(pos_list[pos] * selection <= max_players)
    
    WAR = WAR_vec * selection
    problem = cp.Problem(cp.Maximize(WAR), constraints)
    problem.solve()
    print("***********value is {}".format(problem.value)) 
    all_df = all_df.reset_index(drop=True)
    if (problem.status not in ["infeasible", "infeasible_inaccurate", "unbounded"]):
        ret_val = [round(problem.value, 1)] + get_solution(selection.value, all_df)
    else:
        ret_val = [0, 0,0]
    return ret_val

# %%
"""
Now, let's use integer programming to pick and display the team with the highest WARP
"""

# %%
franchise = 'HOU'
teams = [franchise] + team_map.team_map[franchise]
[war, batting_team, pitching_team] = solve_ip(min_decade = 1910, max_decade = 2010, min_players_per_decade = 0, max_players_per_decade = 1,
                                         players_per_position = 1, team = teams)
print(batting_team)
print("\n")
print(pitching_team)

batting_json = batting_team.to_json(orient = 'records')
print(json.dumps(batting_json, indent = 2))
pitching_json = pitching_team.to_json(orient = 'records')
print(json.dumps(batting_json, indent = 2))

