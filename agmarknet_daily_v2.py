# -*- coding: utf-8 -*-
"""agmarknet_daily_v2.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/github/sankpala/crop-price-data-agmarknet/blob/main/agmarknet_daily_v2.ipynb
"""

import time
import bs4
import pandas as pd
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import Select
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import StaleElementReferenceException
from pymongo.mongo_client import MongoClient
from pymongo.server_api import ServerApi
import os

mongo_db = os.environ.get("mongo_db")
mongo_table = os.environ.get("mongo_table")
mongo_url = os.environ.get("mongo_url")
start_day = 1
start_month = 1
start_year = 2010
group_commodity = 'Vegetables'
commodity = 'Coriander(Leaves)'

options = webdriver.ChromeOptions()
options.add_argument('--headless')
options.add_argument('--no-sandbox')
options.add_argument('--disable-dev-shm-usage')

# Use options as a keyword argument when initializing webdriver.Chrome
browser = webdriver.Chrome(options=options)
browser.get("https://agmarknet.gov.in/PriceAndArrivals/SpecificCommodityWeeklyReport.aspx")

def select_values_ini(CommodityGroup,Commodity,Month,Year,Day):
    wait = WebDriverWait(browser, 10)
    wait.until(EC.presence_of_element_located((By.ID, 'cphBody_cboCommodityGroup')))
    select_commodity_element = browser.find_element(By.ID, 'cphBody_cboCommodityGroup')
    select_commodity = Select(select_commodity_element)
    select_commodity.select_by_visible_text(CommodityGroup)

    select_commodity_element1 = browser.find_element(By.ID, 'cphBody_cboCommodity')
    select_commodity2 = Select(select_commodity_element1)
    try:
        WebDriverWait(browser, 10).until(
            lambda driver: len(select_commodity2.options) > 1
        )
    except StaleElementReferenceException:
        # If the element is stale, re-locate it and try again
        select_commodity_element1 = browser.find_element(By.ID, 'cphBody_cboCommodity')
        select_commodity2 = Select(select_commodity_element1)
        WebDriverWait(browser, 10).until(
            lambda driver: len(select_commodity2.options) > 1
        )
    select_commodity2.select_by_visible_text(Commodity)


    select_month = browser.find_element(By.ID, 'cphBody_cboMonth')
    select_month1 = Select(select_month)
    select_month1.select_by_visible_text(Month)

    select_year = browser.find_element(By.ID, 'cphBody_cboYear')
    select_year1 = Select(select_year)
    try:
        WebDriverWait(browser, 10).until(
            lambda driver: len(select_year1.options) > 1
        )
    except StaleElementReferenceException:
        # If the element is stale, re-locate it and try again
        select_year = browser.find_element(By.ID, 'cphBody_cboYear')
        select_year1 = Select(select_year)
        WebDriverWait(browser, 10).until(
            lambda driver: len(select_year1.options) > 1
        )
    select_year1.select_by_visible_text(Year)

    date_string = f"{Month} {Day}, {Year}"
    # Wait for the anchor element to be present in the DOM
    anchor_locator = f"//a[@href=\"javascript:__doPostBack('ctl00$cphBody$Calendar1','{time_delta(date_string)}')\"]"
    anchor_element = WebDriverWait(browser, 5).until(
        EC.presence_of_element_located((By.XPATH, anchor_locator))
    )
    anchor_element.click()

    submit_button = WebDriverWait(browser, 5).until(
        EC.presence_of_element_located((By.ID, 'cphBody_btnSubmit'))
    )
    submit_button.click()
def check_options(element_id):
    # Use WebDriverWait instead of time.sleep()
    WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.ID, element_id))
    )
    select = Select(browser.find_element(By.ID, element_id))
    values = select.options
    return 1 if len(values) > 0 else check_options(element_id)

def scrape_table():
    res = browser.page_source
    return res

def go_back():
    browser.execute_script("window.history.go(-1)")
def go_back_button():
    back_button = WebDriverWait(browser, 10).until(
        EC.presence_of_element_located((By.ID, 'cphBody_ButtonBack'))
    )
    WebDriverWait(browser, 10).until(
        EC.element_to_be_clickable((By.ID, 'cphBody_ButtonBack'))
    )
    back = browser.find_element(By.ID,'cphBody_ButtonBack')
    back.click()

def time_delta(result_date):
  start_date_str = "2000-01-01"
  start_date = datetime.strptime(start_date_str, "%Y-%m-%d")
  result_date = datetime.strptime(result_date, "%B %d, %Y")

  # Calculate the difference in days
  days_difference = (result_date - start_date).days
  return days_difference
def refresh():
  browser.get("https://agmarknet.gov.in/PriceAndArrivals/SpecificCommodityWeeklyReport.aspx")

def connect_db():
  uri = mongo_url
  # Create a new client and connect to the server
  client = MongoClient(uri, server_api=ServerApi('1'))
  client.admin.command('ping')
  db = client[mongo_db]
  table = db[mongo_table]
  return table

def delete_duplicate(tb):
  today = datetime.now()
  thirty_days_ago = today - timedelta(days=30)
  pipeline = [
      {"$match": {"Date": {"$gte": thirty_days_ago}}},
      {"$group": {"_id": "$Date", "maxLastRefreshDate": {"$max": "$Last_Refresh_Date"}}}
    ]
  # Execute the aggregation pipeline
  result = tb.aggregate(pipeline)
  # Delete documents with Last_Refresh_Date not equal to maxLastRefreshDate for each Date
  for entry in result:
      date = entry['_id']
      max_last_refresh_date = entry['maxLastRefreshDate']
      # Delete documents with Date equal to date and Last_Refresh_Date not equal to max_last_refresh_date
      delete_result = tb.delete_many({"Date": date, "Last_Refresh_Date": {"$ne": max_last_refresh_date}})

def output_data(res):
  soup = bs4.BeautifulSoup(res, 'html.parser')
  table = soup.find('table', id='cphBody_gridRecords')
  column_names = [th.text.strip() for th in table.find('tr').find_all('th')]
  column_names.append('State')
  #print(column_names)
  # Extract data from the table
  data = []
  for x in soup.find_all('table',id='cphBody_gridRecords'):
    for row in x.find_all('tr')[1:]:
        row_data = [col.get_text(strip=True) for col in row.find_all(['th', 'td'])]
        data.append(row_data)
  data1=[]
  for xo in data:
    x1=xo
    if len(xo)==1:
      State=xo[0]
    else:
      x1.append(State)
      data1.append(x1)
  df = pd.DataFrame(data1,columns=column_names)
  return df

def date_sequence(min_date,end_date):
  date_sequence = []

  # Use a for loop to generate the sequence
  current_date = min_date
  while current_date <= end_date:
      date_sequence.append(current_date)
      current_date += timedelta(days=1)

  return date_sequence

def run_main(group_commodity,commodity,month,year,day):
  global refresh_f
  refresh_f = 0
  try:
    select_values_ini(group_commodity,commodity,month,year,day)
  except:
    try:
      select_values_ini(group_commodity,commodity,month,year,day)
    except:
      try:
        select_values_ini(group_commodity,commodity,month,year,day)
      except:
        refresh()
        refresh_f=1

fn=0
while fn==0:
  try:
    table=connect_db()
    m_date = table.find_one(sort=[('Date', -1)])

    if m_date is not None:
        min_date = m_date['Date'] - timedelta(days=5)
    else:
        min_date = datetime(int(start_year), int(start_month), int(start_day))

    # For MongoDB
    date_seq=date_sequence(min_date,datetime.today())
    refresh_f=1
    refresh_n=0
    date_index=0
    file_index=0
    for d in date_seq:
      refresh_f=1
      refresh_n=0
      # Extract individual components
      month = d.strftime("%B")
      year = d.strftime("%Y")
      day = d.strftime("%d")
      while refresh_f==1 and refresh_n<=3:
        run_main(group_commodity,commodity,month,year,day)
        refresh_n=refresh_n+1
      if refresh_n<=3:
        date_index=date_index+1
        res=scrape_table()
        try:
          data=output_data(res)
          data['Date']=d
          data['Last_Refresh_Date']=datetime.now()
        except:
          print(f"No data found for {d}")
          data = pd.DataFrame({'Date':[d]})
        data_list = data.to_dict(orient='records')
        table.insert_many(data_list)
        print(f"Data Loaded: {d}")
        try:
          go_back_button()
        except:
          refresh()

    delete_duplicate(table)
    fn=1
  except:
    time.sleep(900)
