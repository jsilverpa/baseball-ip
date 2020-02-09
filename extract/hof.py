import pandas as pd
import pdb

field_pos = ['C', '1B', '2B', '3B', 'SS', 'OF', 'DH']
#create a csv for each non pitcher


def create_fielder_positions():
	df = pd.read_csv("../data_priv/war_b_bp.csv", ',')
	#first group by decade
	df = df.groupby([df.BATTER, df.NAME, (df.YEAR//10)*10]).sum()
	
	#first create new "OF" position
	df['G_OF'] = df['G_LF'] + df['G_CF'] + df['G_RF']
	
	for pos in field_pos:
		#create the <pos>_bp.csv to represent players who were this position for the decade
		query_statement = ""
		minus_pos = field_pos[:]
		minus_pos.remove(pos)   #make deep copy and remove current pos
		for next_pos in minus_pos:
			if (len(query_statement) > 0):
				query_statement = query_statement + " and " 
			query_statement = query_statement + "(G_{} > G_{})".format(pos, next_pos)
		df_pos = df.query(query_statement)
		
		df_pos.to_csv("../data_priv/{}_bp.csv".format(pos))
		
	


pitcher_pos =["RHP", "LHP"]
def create_pitcher_positions():
	df = pd.read_csv("../data_priv/war_p_bp.csv", ',')
	people = pd.read_csv("../data_priv/BP_players.csv", sep=";")
	#first copy WARP to DRA_PWARP for 1951 because DRA_PWARP is missing for 1951.   WARP is pretty close to DRA_PWARP
	df.DRA_PWARP = df.WARP.where(df.YEAR == 1950, df.DRA_PWARP)
	#first group by decade
	df = df.groupby([df.PITCHER, df.NAME, (df.YEAR//10)*10]).sum().rename(columns={'YEAR':'AAA'})  #avoid duplicate YEAR columns (i don't really understand this)
	df = df.reset_index()
	
	#append info about whether they throw lefty or righty
	df = pd.merge(df, people[['PLAYERID','BASEBALLREFERENCECODE', 'THROWS']], how='left', left_on=['PITCHER'], right_on=['PLAYERID'])
	
	for pos in pitcher_pos:
		#create the <pos>_bp.csv to represent players who were this position for the decade
		df_pos = df.loc[df.THROWS == pos[0]]	
		df_pos.to_csv("../data_priv/{}_bp.csv".format(pos))

		
	

