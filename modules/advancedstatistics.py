#!/usr/bin/python

import urllib2 
import simplejson
import json
import pandas as pd
import re
import numpy as np
import ast
import sys
import os
#from pandas.io.json import json_normalize

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../modules')))
from tabulardata import loadcodes, load_api_data, countryset, json_dict, createframe, combinedata, data2panel,  moderncodes
from config import configuration, dataverse2indicators, load_dataverse, findpid, load_metadata, load_fullmetadata
from historical import load_historical, histo
from paneldata import panel2dict, paneldatafilter, panel2csv

def loadpanel(jsonapi, yearmin, yearmax, ctrlist):
    cleanedpanel = ''
    dataframe = load_api_data(jsonapi, '')

    allcodes = {}
    panel = []
    for dataitem in dataframe: 
        handle = dataitem['handle']        
        (dataset, codes) = paneldatafilter(dataitem['data'], int(yearmin), int(yearmax), ctrlist, handle)    
        if not dataset.empty:                
            panel.append(dataset)

    if panel:
        totalpanel = pd.concat(panel)
        cleanedpanel = totalpanel.dropna(axis=1, how='any')
        cleanedpanel = totalpanel
	# Replace empty values with NaN
	cleanedpanel = cleanedpanel.replace(r'', np.nan, regex=True)

    return (panel, cleanedpanel)

def handle2statistics(handles, cleanedpanel):
    maindataframe = []
    for handle in handles:
        newpanel = cleanedpanel[cleanedpanel['handle'] == handle]
        newpanel = newpanel.drop('handle', axis=1)
        ypanel = newpanel.columns
        newpanel = newpanel.reset_index()
        newpanel = newpanel.drop('Code', axis=1)
        cdataframe = {}
        if handle:
            data = {}
            arrdata = newpanel #.ix[code]

            ctrdata = pd.DataFrame(arrdata)
            data['Handle'] = handle
            # Mean
            tmpframe = ctrdata.mean()
            data['Mean'] = tmpframe.mean()
            # Min
            tmpframe = ctrdata.min()
            data['Min'] = tmpframe.min()
            # Max
            tmpframe = ctrdata.max()
            data['Max'] = tmpframe.max()
            # Std
            tmpframe = ctrdata.std()
            data['Std'] = tmpframe.std()
            # Count
            tmpframe = ctrdata.count()
            data['N'] = tmpframe.count()
            # Yearmin 
            ymin = min(ypanel)
            # Min
            ymax = max(ypanel)
            period = str(ymin) + '-' + str(ymax)
            data['Period'] = period
            maindataframe.append(data)

    return maindataframe

def statistics2table(data):
    html = "<table border=1>\n<tr bgcolor=#efefef>\n"
    for item in sorted(data[0]):
        html = html + "<td>" + str(item) + "</td>" 
    html = html + "</tr>\n"
    for dataitem in data:
        html = html + "\t<tr>"
        for item in sorted(dataitem):
            html = html + "<td>" + str(dataitem[item]) + "</td>"
        html = html + "</tr>\n"
    html = html + "</table>"
    return html

def data2statistics(handles, cleanedpanel):
    maindataframe = {}    
    for handle in handles:    
        newpanel = cleanedpanel[cleanedpanel['handle'] == handle]   
        newpanel = newpanel.drop('handle', axis=1)    
        cdataframe = {}
        for code in newpanel.index:
            data = {}
            arrdata = newpanel.ix[code]        
        
            ctrdata = pd.DataFrame(arrdata) 
            # Mean
            data['Mean'] = ctrdata.mean(axis=0).to_json()
            # Min
            data['Min'] = ctrdata.min(axis=0).to_json()
            # Min
            data['Max'] = ctrdata.max(axis=0).to_json()
            # Std
            data['Std'] = ctrdata.std(axis=0).to_json()
            # Count
            data['N'] = ctrdata.count(axis=0).to_json()
            # Yearmin 
            ymin = min(ctrdata.index)
            # Min
            ymax = max(ctrdata.index)        
            period = str(ymin) + '-' + str(ymax)        
            data['Period'] = period
            cdataframe[code] = data
        maindataframe[handle] = cdataframe
        
    return maindataframe

def read_measure(measure, data):
    value = ''
    if measure:            
        values = {}      
        value = ''
        try:
            values = json.loads(data[measure])
            for x in values:
                value = values[x]
        except:
            value = data[measure]            
            
    return value    
                    
def statistics_tojson(maindataframe, modern):
    html = '<table border=1 style="border: solid 0.5px;">'
    codehtml = ''
    codehtml = codehtml + '<tr>'

    for handle in maindataframe:
        infodata = maindataframe[handle]
	datahtml = ''
        htmlhandle = "<tr><td>" + str(handle) + "</td><td>Country</td>"
	for somecode in infodata:
	    m = infodata[somecode]

	for measure in sorted(m):
	    htmlhandle = htmlhandle + "<td>" + str(measure) + "</td>"        
	htmlhandle = htmlhandle + "</tr>"

        codehtml = ''
        for code in infodata:
	    noname = ''
	    try:
	        country = str(modern[code])
	    except:
	 	country = str(code)

	    active = 0
            countryitem = "<tr><td>&nbsp;</td>\n\t<td>" + country + "</td>\n"
            data = infodata[code]
            minvalue = read_measure('Mean', data)              
            if minvalue != None:
                for measure in sorted(data):            
                    values = {}      
                    value = ''
                    try:
                        values = json.loads(data[measure])
                        for x in values:
                            value = values[x]
                    except:
                        value = data[measure]       

		    if not value:
			value = "&nbsp;"
                    countryitem = countryitem + "\t<td>" + str(value) + "</td>\n"      
		    active = 1
            
            if active:                
                datahtml = datahtml + countryitem + "</tr>\n"   

       	htmlhandle = htmlhandle + datahtml
        html = html + htmlhandle 
    html = html + "</table>"
    return html

def advpanel2dict(cleanedpanel):
    data = cleanedpanel.reset_index().to_dict()
    codes = data['Code']
    handlesdata = data['handle']
    handles = {}
    vhandles = {}
    for i in handlesdata:
        thishandle = handlesdata[i]
        try:
            hinfo = handles[thishandle]
        except:
            hinfo = []
        
        hinfo.append(i) 
        handles[thishandle] = hinfo
        for i in hinfo:
            vhandles[i] = thishandle

    rcodes = {}
    i = 0
    countries = {}
    for i in codes:
        code = codes[i]
        try:
            cdata = countries[code]
        except:
            cdata = []
        
        cdata.append(i)
        countries[code] = cdata
        rcodes[code] = i
        i = i +1

    panelout = {}
    header = 'Country,'
    for handle in handles:
        header = header + str(handle) + ','
    header = header + str('Year')
    
    return (header, data, countries, handles, vhandles) 
