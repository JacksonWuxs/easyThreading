# easyThreading
![](https://img.shields.io/badge/Python2-pass-green.svg)![](https://img.shields.io/badge/Python3-pass-green.svg)![](https://img.shields.io/badge/Download-PyPi-green.svg)![](https://img.shields.io/badge/License-GNU-blue.svg)

#### What is easyThreading?

This program offers you a threading pool with beautiful APIs.

#### How does it work?

Inside easyThreading, we manage all your worker threading by keeping a daemon thread.

#### Usages

* You are going to collect the NBA game information as follow:

```python
import requests
import json

url = "http://matchweb.sports.qq.com/kbs/list?from=NBA_PC&columnId=100000&startTime={}&endTime={}&callback=ajaxExec&_=1540442149442"     
header = {"User-Agent": "Mozilla/5.0 (Windows NT 6.1; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/68.0.3440.106 Safari/537.36"}

def getDate(begin_year):
    for year in range(begin_year, 2020):
        for month in range(1, 12):
            month = str(month).rjust(2, '0')
            for day in range(1, 32):
                day = str(day).rjust(2, '0')
                yield ('%s-%s-%s'  % (year, month, day), )

def getMatch(url, header, date):
    web_data = requests.get(url.format(date, date), headers=header)
    web_data.encoding = 'utf-8'
    data = json.loads(web_data.text[9:-1])['data']
    if date in data:
        return [match for match in data[date]]
```

* Launch your workers

```python
from easyThreadPool import Pool

# since `url` and `header` are the same all the time, 
# we settle down them when we initial the Pool
with Pool(max_size=100, target=getMatch, args=(url, header)) as pool:
	
	# different parameters are created by function getDate
	iter_parameters = getDate(begin_year=2015)
	
	# create workers for your task when there are not full in the pool
	pool.map(iter_parameters)
	
	# block the main thread until all workers are done
	pool.join()
	
	# get match information from all workers
	# THIS IS A THREAD SAFETY OPERATION !!!
	results = pool.get_results() # return results as a list
	
	# read the report 
	pool.report()
    
''' output
 - Threading Pool for task getMatch
   * current Pool is Active: True
   * totally lunched 341 threads
   * current working 0 threads
   * average working time 0.25 seconds
   * average waiting time 0.00 seconds
 '''
```