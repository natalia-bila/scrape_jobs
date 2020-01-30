import requests
from bs4 import BeautifulSoup

import time
import numpy as np
import pandas as pd

import re
import ast

class Vacancy:
    def __init__(self, location, title, company=None, description=None, salary=None, url=None, level=None):
        self.url = url
        self.location = location
        self.title = title
        self.company = company
        self.salary = salary
        self.description = description
        self.level = level
        
    def to_list(self):
        return [self.salary, self.location, self.level, self.title, self.company, self.description]
    
    def __str__(self):
        return '%s\t%s\t%s\t%s' %(self.title, self.company, self.location, self.salary)

def get_all_locations():
    data = requests.get('https://rabota.ua/jobsearch/vacancy_list?')
    soup = BeautifulSoup(data.content,'html')
    string = re.search(r'var cities = (.*?);', str(soup.body)).group(1) # get locations list from the page code
    string = string.replace('true', 'True')
    string = string.replace('false', 'False')
    cities_list = ast.literal_eval(string)
    return dict([(reg['label'],reg['id']) for reg in cities_list])

def get_region_name(location):
    if location.lower() == 'все регионы':
        return 'украина'
    elif location.lower() == 'другие страны':
        return 'другие_страны'
    if not location in locations_dict.values() or location.lower() not in ('все регионы','другие страны'):
        raise KeyError(f'Location {location} isn\'t available') 
    return location

class PageKey:
    def __init__(self):
        self.current_page = 1
    
    def __iter__(self):
        return self
    
    def __next__(self):
        self.current_page += 1
        return '%s' % self.current_page
    
def get_all_vacancies_links(vacancy_name):
    return get_local_vacancies_links(vacancy_name, location='все регионы')

def get_local_vacancies_links(vacancy_name, location):

    location = get_region_name(location)
    page_key = PageKey()
    links = []
    print(f'Searching in \'{location}\'...', end='\r')
    k = 0
    while True:
        k+=1
        time.sleep(np.random.uniform(low=0.1, high=0.3)) # sleep time to look more human
        if k==1:
            url = f'https://rabota.ua/zapros/{vacancy_name}/{location}/?salaryType=1'
        else:
            url = f'https://rabota.ua/zapros/{vacancy_name}/{location}/pg{next(page_key)}?salaryType=1'
        data = requests.get(url)
        soup = BeautifulSoup(data.content,'html')
        try:
            vacancies_number = int(soup.find('span', {'class': "fd-fat-merchant"}).get_text())
        except:
            #match might be a NoneType
            break            
        if not vacancies_number:
            #if vacancies number is 0
            break
        links_page = []
        for aTag in soup.find_all('a', {'class': 'f-visited-enable ga_listing'}):
            links_page.append('https://rabota.ua' + aTag.get('href'))
        if not links_page:
            print('%4s vacancies were added from \'%s\''%(len(links),location))
            return links
        links.extend(links_page)
    print(' '*80, end='\r')
    
def get_location(soup):
    try:
        return soup.find('span', {'class':"f-vacancy-city-param"}).get_text()
    except:
        try:
            tag = soup.find('li',{'class':"d-ph-itemAddress", 'id':"d-city"})
            return tag.find('span',{'class':"d-ph-value"}).get_text()
        except:
            return None

def get_title(soup):
    try:
        return soup.find('h1', {'class': "f-vacname-holder fd-beefy-ronin f-text-black"}).get_text()
    except:
        try:
            return soup.find('h1').get_text()
        except:
            return None

def get_company(soup):
    try:
        return soup.find('span', {'itemprop':"name"}).get_text()
    except:
        try:
            tag = soup.find('li', {'class':"d-ph-item d-ph-full", 'id':"d-company"})
            return tag.find('span', {'class':"d-ph-value"}).get_text()
        except:
            return None

def get_salary(soup):
    try:
        salary_string = soup.find('p' ,{'class':"f-salary-holder fd-syoi f-text-black"}).get_text()
        salary_string = ''.join([char for char in salary_string if char.isdigit()])
    except:
        try:
            tag = soup.find('li',{'class':"d-ph-item",'id':"d-salary"})
            salary_string = tag.find('span', {'class':"d-ph-value"}).get_text()
            return int(''.join([char for char in salary_string if char.isdigit()]))
        except:
            return None
    return int(salary_string)

possible_levels = ['trainee','intern','стажер','junior','джуниор',
                   'middle','regular','миддл','мидл',
                   'senior','синиор','синьор','director',
                   'lead','architect','research']
def get_level(soup):
    try:
        tag = soup.find('li', {'class':"fd-craftsmen"})
        return tag.get_text().split('/')[0].lower()
    except:
        try:
            title = get_title(soup).lower()
            for level in possible_levels:
                if level in title:
                    return level
        except:
            return None

def get_description(soup):
    try:
        return soup.find('div', {'class':"d_des"}).get_text()
    except:
        try:
            return soup.find('div', {'class':"f-vacancy-description-inner-content",'itemprop':"description"}).get_text()
        except:
            return None

def create_vacancies_list(vacancies_url):
    vacancies_list = []
    for url in  vacancies_url:
        
        time.sleep(np.random.uniform(low=0.1, high=0.3))
        data = requests.get(url)
        soup = BeautifulSoup(data.content,'html')

        title = get_title(soup)
        company = get_company(soup)
        salary = get_salary(soup)
        location = get_location(soup)
        description = get_description(soup)
        level = get_level(soup)

        if title and location:
            vacancy = Vacancy(location=location, title=title, company=company, level=level,
                              description=description, url=url, salary=salary)
            vacancies_list.append(vacancy)
            print('%4s/%s vacancy(es) were successfully parced' % (len(vacancies_list), len(vacancies_url)), end='\r')    
    return vacancies_list
    
vacancies_url = get_all_vacancies_links('аналитик')
vacancies_list = create_vacancies_list(vacancies_url)
dataFrame = pd.DataFrame([vacancy.to_list() for vacancy in vacancies_list],
                         columns = ['Salary','Location','Level','Title','Company','Description'])
dataFrame.Level = dataFrame.Level.apply(lambda x: 'unknown' if x is None else x)
dataFrame.head(15)

    