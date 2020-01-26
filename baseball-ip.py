import numpy as np
import cvxpy as cp
import pandas as pd
from tabulate import tabulate

import pdb
MIN_DECADE = 1920

batter_header = ['Name', 'Decade', 'Pos', 'WARP', 'BA', 'OBP', 'SLG', 'H', 'HR', 'RBI', 'R']
pitcher_header = ['Name', 'Decade', 'Pos', 'WARP', 'Record', 'ERA', 'WHIP', 'K', 'IP']
def print_team(team, is_pitcher):
	team_table = []
	for iter, player in team.iterrows():
		player_row = [player.NAME, player.YEAR, player.POS, "{:.1f}".format(player.WARP)]
		if (is_pitcher):
			record =str(round(player.W)) + "-" + str(round(player.L))
			era = "{:.2f}".format(round(player.ER/player.IP * 9, 2))
			whip = "{:.3f}".format(round((player.BB + player.H)/player.IP, 3))
			player_row.extend([record, era, whip, player.SO, round(player.IP)])
		else:
			ba = "{:.3f}".format(round(player.H/player.AB,3))
			obp = "{:.3f}".format(round((player.H+player.BB+player.HBP)/(player.AB+player.BB+player.HBP+0),3))
			slg = "{:.3f}".format(round(player.TB/player.AB,3))
			player_row.extend([ba, obp, slg,  player.H, player.HR, player.RBI, player.R])
		team_table.append(player_row)
	if (is_pitcher):
		print(tabulate(team_table, headers= pitcher_header, tablefmt="psql", disable_numparse = True))
	else:
		print(tabulate(team_table, headers= batter_header, tablefmt="psql", disable_numparse=True))
	print("\n")

field_pos = ['C', '1B', '2B', '3B', 'SS', 'OF']
pitcher_pos = ['RHP', 'LHP']

def print_solutions(ar, df):
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
	print_team(picked_batters, False) 
	print_team(picked_pitchers, True) 


def print_top_players(positions, min_year = 1920, count = 10):
	for pos in positions:
		pos_df = pd.read_csv("data/" + pos + ".csv")
		pos_df['POS'] = pos
		pos_df = pos_df.loc[pos_df.YEAR >= min_year]
		pos_df = pos_df.sort_values(by="WARP", ascending = False)
		is_pitcher = pos in pitcher_pos
		print_team(pos_df.head(count), is_pitcher)
		print("\n")

	



pos_list = {}
#first initialize all the dict items to empty vector
for pos in field_pos + pitcher_pos:
    pos_list[pos] =[]

decade_vec = []
for decade in range (MIN_DECADE, 2021, 10):
        decade_vec.append([])

name_vec =[]
WAR_vec = []
all_df = pd.DataFrame()
for pos in field_pos + pitcher_pos:
    #pdb.set_trace()
    df = pd.read_csv("data/" + pos + ".csv")

    # remove everyone with insignificant WAR and years prior to first decade
    df = df.loc[df['WARP'] > 4]
    df = df.loc[df['YEAR'] >= MIN_DECADE]
    #create pos column
    df['POS'] = pos

    all_df = all_df.append(df)

    zeroes = np.zeros(len(df))
    ones = np.ones(len(df))

    #set the position vector
    for pos_list_item in field_pos + pitcher_pos:
        if (pos == pos_list_item):
            pos_list[pos_list_item].extend(ones)
        else:
            pos_list[pos_list_item].extend(zeroes)

    #set the decade vectors
    for decade in range(MIN_DECADE, 2021, 10):
        this_decade = np.where(df['YEAR'] == decade, 1, 0)
        decade_vec[(decade - MIN_DECADE) // 10].extend(this_decade)

    name_vec.extend(df['NAME'].to_list())
    WAR_vec.extend(df['WARP'].to_list())
			




selection = cp.Variable(len(name_vec), boolean = True)

constraints = []
for i in range(0, len(decade_vec)):
    #1 player per decade
    constraints.append(decade_vec[i] * selection <= 1)

for pos in field_pos + pitcher_pos:
    max_players = 1
    if (pos == 'OF'):
        max_players = 3
    constraints.append(pos_list[pos] * selection <= max_players)

#constraints.append(position_vec * selection == 1)
#pdb.set_trace()

WAR = -(WAR_vec * selection)

problem = cp.Problem(cp.Minimize(WAR), constraints)
problem.solve()

all_df = all_df.reset_index(drop=True)
if (problem.status not in ["infeasible", "infeasible_inaccurate", "unbounded"]):
    print("MAX WAR is {}".format(-problem.value))
    print_solutions(selection.value, all_df)
else:
    print("MAX WAR is Infeasible")
