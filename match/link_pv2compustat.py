import pandas as pd
import sqlite3
import my_own_handy_functions as mf
from itertools import combinations 
import re

prefix = "pv_"
logfile = ''

attach_sql = ";"
attach_name = ""

i = 2
task_i_suffix = f'task{i}'
suffix = "all_top5"

db_folder = f"../../../Apps/CBS_ResearchGrid/{prefix}search_result_db/"
db = db_folder + f"{prefix}search_{suffix}.db"
con = sqlite3.connect(db)
print(mf.show_tables(con))

sql = f"select * from {prefix}search_" + suffix + attach_sql
df_pv = pd.read_sql(sql, con)
try:
    df_pv = df_pv.drop('index', 1)
except:
    pass

prefix = "compustat_"
db_folder = f"../../../Apps/CBS_ResearchGrid/{prefix}search_result_db/"
db = db_folder + f"{prefix}search_{suffix}.db"
con = sqlite3.connect(db)
print(mf.show_tables(con))
sql = f"select * from {prefix}search_" + suffix + attach_sql
df_compustat = pd.read_sql(sql, con)
try:
    df_compustat = df_compustat.drop('index', 1)
except:
    pass
df_compustat = df_compustat.drop(['gvkey', 'compustat_conml'], 1)
df_compustat = df_compustat.drop_duplicates(['compustat_newname'])

list_newname_compustat = list(df_compustat['compustat_newname'])
list_urls5_compustat = list(df_compustat['urls5'])
list_newname_pv = list(df_pv['pv_newname'])
list_urls5_pv = list(df_pv['urls5'])

## clean the url a bit
http_re = re.compile(r"^http\:\/\/|^https\:\/\/|\/$")

## index all the unique urls
set_url_compustat = set(http_re.sub('',url) for urls5 in list_urls5_compustat for url in eval(urls5))
set_url = set(http_re.sub('',url) for urls5 in list_urls5_pv for url in eval(urls5))
set_url.update(set_url_compustat)

list_url = list(set_url)
dict_all_url_index = {}
for i in range(0, len(list_url)):
    dict_all_url_index.update({i: list_url[i], list_url[i]: i})

### change 5 urls to their corresponding indexes 
def newname_url_index(list_urls5, list_newname):
    dict_newname_url_index = {}
    for i in range(0, len(list_newname)):
        newname = list_newname[i]
        urls5 = eval(list_urls5[i])
        urls5_index = frozenset([dict_all_url_index[http_re.sub('',url)] for url in urls5])
        dict_newname_url_index[newname] = urls5_index
    return dict_newname_url_index

# dictionary of newname to a set of 5 urls                
dict_newname_url_index_pv = newname_url_index(list_urls5_pv, list_newname_pv)
dict_newname_url_index_compustat = newname_url_index(list_urls5_compustat, list_newname_compustat)

# construct a dictionary of n-urls to newname
##### n means that how many matches of urls are required here
#### suf means suffix
def urls_index_dict(n, # number of urls to be hashed 
                    suf, # '_pv' or '_compustat'
                    ):
    
    dict_urls = {}
    list_newname = globals()[f"list_newname{suf}"]
    for i in range(0, len(list_newname)):
        newname = list_newname[i]
        urls5_index = globals()[f"dict_newname_url_index{suf}"][newname]
        if len(urls5_index) >= n:
            # hash all the 5Cn combinations of urls
            urls5_index_c5n = combinations(urls5_index, n)
            for urls_item in urls5_index_c5n:
                urls_key = frozenset(urls_item)
                if urls_key not in dict_urls:
                    dict_urls[urls_key] = {newname}
                else:
                    dict_urls[urls_key].update({newname})
    return dict_urls
    
dict_pv2compustat = [{}, {}, {}, {}]
#### matching based on 5/4/3/2 urls
for n in range(5,1,-1):
    # hash all 5Cn combinations of urls
    dict_urls_pv = urls_index_dict(n, '_pv')
    dict_urls_compustat = urls_index_dict(n, '_compustat')
    print(f"{n} loading done")
    
    # for each hashed n-url in compustat
    for key, value in dict_urls_compustat.items():
        # if this hashed n-url can also be found in PV, give a match
        if key in dict_urls_pv:
            newname_compustat = list(value)
            newname_pv_list = list(dict_urls_pv[key])
            for newname_pv in newname_pv_list:
                if newname_pv not in dict_pv2compustat[5-n]:
                    dict_pv2compustat[5-n][newname_pv] = set(newname_compustat)
                else:
                    dict_pv2compustat[5-n][newname_pv].update(set(newname_compustat))
    print(f"{n} dict done")
    dict_urls_pv = {}
    dict_urls_compustat = {}            

mf.pickle_dump(dict_pv2compustat, 'dict_pv2compustat')
mf.pickle_dump(dict_all_url_index, 'dict_all_url_index_pv2compustat')
