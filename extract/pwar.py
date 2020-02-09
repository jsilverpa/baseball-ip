import pandas as pd
import requests
from selenium import webdriver
from selenium.webdriver.common.keys import Keys

import pdb
from bs4 import BeautifulSoup


#process to generate <pos>.csv 
#pull the list of pitchers  and batters from br database.  columns should include bp id  and wins.   store this in war_p_bp and war_b_bp
#run hof.create_pitcher_positions() and hof.create_fielder_positions() to create <pos>_bp.csv
#run pwar.pull_br_war(hof.field_pos + hof.pitcher_pos) to pull the actual war from br and store in data/<pos>.csv
#We need to do this since BP does not include WAR for older pitchers


def pull_br_war(positions):
	people = pd.read_csv("../data_priv/BP_players.csv", sep=";")
	options = webdriver.ChromeOptions()
	options.add_argument('headless')
	driver = webdriver.Chrome(chrome_options=options)

	for pos in positions:
		is_pitcher = 0
		if (pos == 'LHP') or (pos == 'RHP'):
			is_pitcher=1
		pit = pd.read_csv("../data_priv/{}_bp.csv".format(pos))
		if (is_pitcher):
			pit = pit.groupby([pit.PITCHER, pit.NAME, (pit.YEAR//10)*10]).sum().rename(columns={'YEAR':'AAA'})
		else: 
			pit = pit.groupby([pit.BATTER, pit.NAME, (pit.YEAR//10)*10]).sum().rename(columns={'YEAR':'AAA'})
			
		pit = pit.reset_index()
		pit = pit.drop(["AAA"], axis=1)
	
		if (is_pitcher):
			#only look at players with more wins than 70 for a decade
			x = pit.loc[pit['W'] > 5]	
			x = pd.merge(x, people[['BASEBALLREFERENCECODE', 'PLAYERID']], how='left', left_on='PLAYERID', right_on='PLAYERID')
		else:
			x = pit.loc[pit['AB'] > 400]	
			#batters don't have PLAYERID yet
			x = pd.merge(x, people[['BASEBALLREFERENCECODE', 'PLAYERID']], how='left', left_on='BATTER', right_on='PLAYERID')
		#remove duplicate player names since we grouped by decade
		canon = x.drop_duplicates(subset="PLAYERID")
		canon.reset_index(drop=True, inplace=True)
		table = pd.DataFrame()
		for iter, row in canon.iterrows():	
			#if (iter %400 != 0):
			#	continue
			#if (iter != 1091):
				#continue
			print ("{}/{}".format(iter,len(canon)))
			br_name = row['BASEBALLREFERENCECODE']	
			if (isinstance(br_name, str) == False):	  #some baseball reference codes have not yet been updated
				print("No baseballref for {}.   BP_Players needs updating".format(row.NAME))
				continue
			url = "https://www.baseball-reference.com/players/{}/{}.shtml".format(br_name[0], br_name)
			print("fetching url : {}".format(url))
			driver.get(url)
			sp = driver.page_source
	
			soup = BeautifulSoup(sp, "lxml")
			f = open("xx.junk", "w")
			f.write(str(soup))
	
			if (is_pitcher):
				nextTable = get_table(soup, "pitching_value")
				if (nextTable is None):
					continue
				nextTable["PITCHER"] = row["PITCHER"]
			else:
				if (nextTable is None):
					continue
				nextTable = get_table(soup, "batting_value")
				nextTable["BATTER"] = row["BATTER"]
			if nextTable.empty:
				continue;
			nextTable["NAME"] = row["NAME"]
			nextTable['Year'] = pd.to_numeric(nextTable["Year"])
			nextTable['WAR'] = pd.to_numeric(nextTable["WAR"])
			if (is_pitcher):
				nextTable = nextTable.groupby([nextTable.PITCHER, nextTable.NAME, (nextTable.Year//10)*10])['WAR', 'Tm'].agg({'WAR':'sum', 'Tm' : lambda x: x.mode()[0]}).reset_index()
				#nextTable = nextTable.groupby([nextTable.PITCHER, nextTable.NAME, (nextTable.Year//10)*10]).sum().rename(columns={'Year':'AAA', 'PITCHER':'BBB'}).reset_index()
			else:
				nextTable = nextTable.groupby([nextTable.BATTER, nextTable.NAME, (nextTable.Year//10)*10])['WAR', 'Tm'].agg({'WAR':'sum', 'Tm' : lambda x: x.mode()[0]}).reset_index()
				#nextTable = nextTable.groupby([nextTable.BATTER, nextTable.NAME, (nextTable.Year//10)*10]).sum().rename(columns={'Year':'AAA', 'BATTER':'BBB'}).reset_index()
			table = table.append(nextTable)
			#remove Tot from team since it duplicates years where the person was traded
		if (is_pitcher):
			table = pd.merge(x, table[['PITCHER', 'Year', 'WAR', 'Tm']], how='left', left_on=['PLAYERID','YEAR'], right_on=['PITCHER', 'Year']).rename(columns={"PITCHER_x": "PITCHER"}).drop(["PITCHER_y", "Year"], axis=1)
			#use DRA_PWARP for years >= 1950
			table.WAR = table.DRA_PWARP.where(table.YEAR >= 1950, table.WAR)
			table = table.drop(['PWARP', 'WARP', 'DRA_PWARP'], axis=1)
		else:
			table = pd.merge(x, table[['BATTER', 'Year', 'WAR', 'Tm']], how='left', left_on=['PLAYERID','YEAR'], right_on=['BATTER', 'Year']).rename(columns={"BATTER_x": "BATTER"}).drop(["BATTER_y", "Year"], axis=1)
			#use DRC_WARP for years >= 1950
			table.WAR = table.DRC_WARP.where(table.YEAR >= 1950, table.WAR)
			#only put important stuff in public data
			table = table.drop(['BWARP', 'DRC_WARP', 'YEAR.1'], axis=1)
		table = table.rename(columns = {"WAR" : "WARP", 'Tm' : 'TEAM'})
		table.to_csv("../kaggle/input/baseball-ip/{}.csv".format(pos))

def get_table(soup, table_id):
	table = soup.find("table", id = "{}".format(table_id))
	if (table is None):  #no table.  baseball ref returned 404 
		return None
	data = []
	headings = [th.get_text() for th in table.find("tr").find_all("th")]
	data.append(headings)
	table_body = table.find('tbody')
	rows = table_body.find_all('tr')
	for row in rows:
		splitName = row.find_all('th')
		splitName = splitName[0].text.strip()
		cols = row.find_all('td')
		cols = [ele.text.strip() for ele in cols]
		newRow = [splitName]
		for ele in cols:
			newRow.append(ele)
		data.append(newRow)
	
	data = pd.DataFrame(data)
	data = data.rename(columns=data.iloc[0])
	data = data.reindex(data.index.drop(0))

	return data

