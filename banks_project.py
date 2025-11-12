import requests
from bs4 import BeautifulSoup
import pandas as pd
import numpy as np
from datetime import datetime 
import lxml
import sqlite3

url = "https://web.archive.org/web/20230908091635%20/https://en.wikipedia.org/wiki/List_of_largest_banks"
log_file = "code_log.txt"
target_file = "transformed_data.csv"
csv_path = 'WorldBank.csv'

def log_progress(message):
    timestamp_format = "%Y-%h-%d-%H:%M:%S"
    now = datetime.now()
    timestamp = now.strftime(timestamp_format)  #String format time
    with open(log_file, "a") as f:
        f.write(timestamp + ", " + message + "\n") #Write the timestamp into the log file

table_attributes = ["Name", "MC_USD_Billion"]

def extract(url, table_attributes):
    
    html_page = requests.get(url).text
    data = BeautifulSoup(html_page, 'lxml')
    
    extracted_data = []
    
    tables = data.find_all('table')[0]   
    tbody = tables.find("tbody")
    rows = tables.find_all('tr')
    
    for rows in rows:
        columns = rows.find_all('td')
        if len(columns) < 3:
            continue
       
        a_tag = columns[1].find_all('a')
        name = a_tag[1]['title']

        mc_usd_billion = columns[2].text.strip()
        
        extracted_data.append([name, mc_usd_billion])

        extracted_table = pd.DataFrame(extracted_data, columns = table_attributes)

    return extracted_table


def transform (extracted_table, target_file):
       
    extracted_table['Name'] = extracted_table['Name'].astype('string')
    extracted_table['MC_USD_Billion'] = extracted_table['MC_USD_Billion'].astype('float')
    
    exchange_rate = pd.read_csv('exchange_rate.csv')
    dict = exchange_rate.set_index('Currency').to_dict()['Rate']
    
    extracted_table['MC_GBP_Billion'] = [np.round(x*dict['GBP'],2) for x in extracted_table['MC_USD_Billion']]
    extracted_table['MC_EUR_Billion'] = [np.round(x*dict['EUR'],2) for x in extracted_table['MC_USD_Billion']]
    extracted_table['MC_INR_Billion'] = [np.round(x*dict['INR'],2) for x in extracted_table['MC_USD_Billion']]
    
    return extracted_table


def load_to_csv(transformed_table, csv_path):
    transformed_table.to_csv(csv_path, index = False)


sql_connection = sqlite3.connect('Banks.db')

def load_to_db(transformed_table, sql_connection, table_name):
    transformed_table.to_sql(table_name, sql_connection, if_exists='replace', index=False)



def run_queries(query_statement, sql_connection):
    query_output = pd.read_sql_query(query_statement, sql_connection)
    return query_output


### Executing the ETL ###

log_progress("Preliminaries complete. Initiating ETL process")

extracted_table = extract(url, table_attributes)
log_progress('Data extraction complete. Initiating Transformation process')

transformed_table = transform(extracted_table, target_file)
log_progress("Data transformation complete. Initiating Loading process")

load_to_csv(transformed_table, csv_path)
log_progress('Data saved to CSV file')

load_to_db(transformed_table, sql_connection, 'Largest_banks')
log_progress('Data loaded to Database as a table, Executing queries')

print(run_queries("Select * FROM Largest_banks", sql_connection))
print(run_queries("SELECT AVG(MC_GBP_Billion) FROM Largest_banks", sql_connection))
print(run_queries("SELECT Name from Largest_banks LIMIT 5", sql_connection))
log_progress('Process Complete')

sql_connection.close()
log_progress('Server Connection closed')