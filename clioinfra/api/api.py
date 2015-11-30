# Copyright (C) 2015 International Institute of Social History.
# @author Vyacheslav Tykhonov <vty@iisg.nl>
#
# This program is free software: you can redistribute it and/or  modify
# it under the terms of the GNU Affero General Public License, version 3,
# as published by the Free Software Foundation.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Affero General Public License for more details.
#
# You should have received a copy of the GNU Affero General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.
#
# As a special exception, the copyright holders give permission to link the
# code of portions of this program with the OpenSSL library under certain
# conditions as described in each individual source file and distribute
# linked combinations including the program with the OpenSSL library. You
# must comply with the GNU Affero General Public License in all respects
# for all of the code used other than as permitted herein. If you modify
# file(s) with this exception, you may extend this exception to your
# version of the file(s), but you are not obligated to do so. If you do not
# wish to do so, delete this exception statement from your version. If you
# delete this exception statement from all source files in the program,
# then also delete it in the license file.

from flask import Flask, redirect, make_response, Response, render_template, request, send_from_directory
from twisted.web import http
import webbrowser
import json
import simplejson
import urllib2
import glob
import csv
import xlwt
import os
import sys
import psycopg2
import psycopg2.extras
import pprint
import collections
import ast
import getopt
import numpy as np
import stat
import pandas as pd
import random
import ConfigParser
from subprocess import Popen, PIPE, STDOUT
from random import randint
import brewer2mpl
import string
import pylab as plt
import re
from urllib import urlopen
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../modules')))
from advancedstatistics import loadpanel, statistics2table, handle2statistics, data2statistics, read_measure, statistics_tojson, advpanel2dict
from search import dataset_search, getindicators, dataverse_search, loadjson
import random, string
from download import get_papers, dataset2zip, compile2zip
from tabulardata import loadcodes, load_api_data, countryset, json_dict, createframe, combinedata, data2panel, moderncodes, data2json
from config import configuration, dataverse2indicators, load_dataverse, findpid, load_metadata, load_fullmetadata, pidfrompanel
import matplotlib as mpl
from palettable.colorbrewer.sequential import Greys_8
from data2excel import panel2excel, individual_dataset
from historical import load_historical, histo
from scales import getcolors, showwarning, buildcategories, getscales, floattodec, combinerange, webscales
from storage import data2store, readdata, readdataset, readdatasets, datasetadd, formdatasetquery
from paneldata import paneldatafilter, panel2dict, panel2csv
from datasets import loaddataset, countrystats, loaddataset_fromurl, loadgeocoder, treemap, selectint, buildgeocoder

# Function to create json from dict 
def json_generator(c, jsondataname, data):
	sqlnames = [desc[0] for desc in c.description]
        jsonlist = []
        jsonhash = {}
        
        for valuestr in data:    
            datakeys = {}
            for i in range(len(valuestr)):
               name = sqlnames[i]
               value = valuestr[i]
               datakeys[name] = value
               #print "%s %s", (name, value)
            jsonlist.append(datakeys)
        
        jsonhash[jsondataname] = jsonlist;
        json_string = json.dumps(jsonhash, encoding="utf-8", sort_keys=True, indent=4)

        return json_string

def randomword(length):
   return ''.join(random.choice(string.lowercase) for i in range(length))

# Check if param is location
def is_location(param):
    flag = re.match(r"c\[\d+\]", param)
    try:
        true = flag.group(0)
    except:
        true = 0
        
    return true

# Download ZIP archive
def downloadzip(pid):
    DEBUG = 0
    (fullpath) = ('')
    fullmetadata = {}
    logscale = 0

    config = configuration() 
    API_TOKEN = config['key']
    HOSTNAME = config['dataverseroot']
    cmd = "--insecure -u " + API_TOKEN + ": " + HOSTNAME + "/dvn/api/data-deposit/v1.1/swordv2/statement/study/"
    tmpdir = config['tmpdir']
    filerandom = randomword(10)
    #filerandom = '12345'
    arc = "data" + filerandom + ".zip"
    filename = filerandom  
    finaldir = config['path'] + '/static/tmp'
    # ToDO
    if filename:
        finaldir = str(finaldir) + '/' + str(filename)
        tmpdir = str(tmpdir) + '/' + str(filename)

    try:
        os.mkdir(tmpdir)
        os.mkdir(finaldir)
    except: 
	donothing = 'ok'

    customyear = ''
    fromyear = request.args.get('y[min]')
    toyear = request.args.get('y[max]')
    historical = request.args.get('type[0]')
    (handles, pidslist) = pidfrompanel(pid)
    try:
        if pidslist:
	    fullmetadata = load_fullmetadata(pidslist)
    except:
	showwarning = 1	

    # Log scales switch
    if request.args.get('logscale'):
	logscale = 1

    # Select countries
    customcountrycodes = ''
    f = request.args
    for key in f.keys():
        if is_location(key):
            for value in sorted(f.getlist(key)):
                customcountrycodes = str(customcountrycodes) + str(value) + ','
    if customcountrycodes:
        customcountrycodes = customcountrycodes[:-1]
    
    if handles:
	if historical:
            api = config['apiroot'] + "/collabs/static/data/historical.json"
            (regions, countries, ctr2reg, webmapper, geocoder) = histo(api, '')
            hist = countries
	else:
	    hist = ''

    remote = 'on'
    if remote:
        (classification, dataset) = loaddataset_fromurl(config, config['geocoderhandle'])
    else:
        dataset = loaddataset(handles)

    #geocoder = buildgeocoder(dataset, config)
    (modern, historical) = loadgeocoder(dataset, 'geocoder')
    for handle in handles:
	if remote:
    	    (class1, dataset) = loaddataset_fromurl(config, handle)
	else:
    	    dataset = loaddataset(handles)

	#(cfilter, notint) = selectint(activeindex.values)
	#(moderndata, historicaldata) = loadgeocoder(dataset, '')
	# CHANGE
	#return str(dataset.index)
        (header, panelcells, codes, datahub, data, handle2ind, unit2ind, original) = data2panel(handles, customcountrycodes, fromyear, toyear, customyear, hist, logscale)
	filename = filename + '.xls'
        fullpath = panel2excel(finaldir, filename, header, panelcells, fullmetadata)
    else:
	# Clio format download
	zipfile = get_papers(HOSTNAME, API_TOKEN, cmd, pid, tmpdir, arc, finaldir)
	(alonepid, revid, cliohandle, clearpid) = findpid(pid)
	if alonepid:
	    handles = [ clearpid ]

	for pid in handles:
	    if historical:
                api = config['apiroot'] + "/collabs/static/data/historical.json"
                (regions, countries, ctr2reg, webmapper, geocoder) = histo(api, '')
                hist = countries
	    else:
	        hist = ''
	    filename = filename + '.xls'
	    # 2DEBUG
	    (header, panelcells, codes, datahub, data, handle2ind, unit2ind, originalvalues) = data2panel(handles, customcountrycodes, fromyear, toyear, customyear, hist, logscale)
	    #codes = hist
	    #return str(fullmetadata)
	    metadata = fullmetadata
	    result = individual_dataset(finaldir, filename, handle2ind[pid], unit2ind[pid], datahub, data[pid], codes, metadata)

    try:
        for everypid in handles:
	    # Download papers
            zipfile = get_papers(HOSTNAME, API_TOKEN, cmd, everypid, tmpdir, arc, finaldir)
    except:
	nopapers = 1

    compile2zip(finaldir, arc)
    filename = arc
    return filename

def tableapi():
    # years in filter
    config = configuration()
    customyear = ''
    fromyear = '1500'
    toyear = '2012'
    customcountrycodes = ''
    (aggr, logscale, dataset) = ('',0,'')

    # Select countries
    f = request.args
    for key in f.keys():
	if key == 'loc':
            for value in sorted(f.getlist(key)):
		if value:
		    customcountrycodes = str(customcountrycodes) + str(value) + ','
    if customcountrycodes:
        customcountrycodes = customcountrycodes[:-1]

    handle = "F16UDU"
    # HANDLE
    if request.args.get('handle'):
        handle = request.args.get('handle')
	(dataset, revid, cliohandle, clearpid) = findpid(handle)
    if request.args.get('dataset'):
        dataset = request.args.get('dataset')
    if request.args.get('ctrlist'):
	customcountrycodes = ''
        tmpcustomcountrycodes = request.args.get('ctrlist')
	c = tmpcustomcountrycodes.split(',')
	for ids in sorted(c):
	   if ids:
	       customcountrycodes = str(customcountrycodes) + str(ids) + ','
	customcountrycodes = customcountrycodes[:-1]

    if not customcountrycodes:
	customcountrycodes = '528'
    if request.args.get('yearmin'):
	fromyear = request.args.get('yearmin')
    if request.args.get('yearmax'):
	toyear = request.args.get('yearmax')
    if request.args.get('aggr'):
        aggr = request.args.get('aggr')
    # Log scales switch
    if request.args.get('logscale'):
        logscale = request.args.get('logscale')
    DEBUG = 0

    apifile = str(dataset) + ".json"
    jsonapi = config['apiroot'] + "/collabs/static/data/" + apifile
    dataframe = load_api_data(jsonapi, '')
    loccodes = loadcodes(dataframe)
    (ctr, header) = countryset(customcountrycodes, loccodes)
    indicator = ''
    (frame, years, values, dates, original) = createframe(indicator, loccodes, dataframe, customyear, fromyear, toyear, ctr, logscale, DEBUG)
    names = ['indicator', 'm', 'ctrcode', 'country', 'year', 'intcode', 'value', 'id']

    (csvdata, aggrdata) = combinedata(ctr, frame, loccodes)
    if aggr:
        csvdata = aggrdata

    return (csvdata, aggrdata)

# Search API
def simplesearch(root, qurl, apiroot):
    # Load topics
    #topicurl = apiroot + "/collabs/static/data/dataframe100_0.json"
    topicurl = apiroot + "/api/datasets?handle=Panel[%27hdl:10622/0PCZX5%27]"
    topicsframe = loadjson(topicurl)
    for item in topicsframe:
	topics = item['data']

    # Input
    IDS = getindicators(qurl)

    datasets = dataset_search(root, IDS, topics)
    return datasets

def load_indicators(filename):
    config = configuration()
    csvfile = config['clearance'] + "/collabs/static/data/" + filename
    ufile = urlopen(csvfile)
    data = pd.read_csv(ufile, delimiter='\t')
    df = data
    if csvfile:
        d = [
        dict([
        (colname, row[i])
        for i,colname in enumerate(df.columns)
        ])
        for row in df.values
        ] 
    
    return json.dumps(d)

def load_api_data1(apiurl, fileID):
    jsondataurl = apiurl
    
    req = urllib2.Request(jsondataurl)
    opener = urllib2.build_opener()
    f = opener.open(req)
    dataframe = simplejson.load(f, "utf-8")
    return dataframe

def searchdata(query):
    config = configuration()
    searchapi = config['dataverseroot'] + "/api/search?q=" + query + "&key=" + config['key']
    dataframe = load_api_data(searchapi, '')
    return json.dumps(dataframe)

def medianlimits(dataframe):
    scale = []
    frame1 = []
    frame2 = []
    avg = dataframe.median()
    for value in dataframe:
        if value <= avg:
            frame1.append(value)
        else:
            frame2.append(value)
    avg1 = pd.DataFrame(frame1).median()
    avg2 = pd.DataFrame(frame2).median()
    
    return (dataframe.min(), int(avg1), int(avg), int(avg2), dataframe.max())

def meanlimits(dataframe):
    scale = []
    frame1 = []
    frame2 = []
    avg = dataframe.mean()
    for value in dataframe:
        if value <= avg:
            frame1.append(value)
        else:
            frame2.append(value)
    avg1 = pd.DataFrame(frame1).mean()
    avg2 = pd.DataFrame(frame2).mean()

    return (dataframe.min(), int(avg1), int(avg), int(avg2), dataframe.max())

def round_it(x):
    g = round(x)
    if request.args.get('code'):
        m = r'LCI'
        isindex = re.match(m, request.args.get('code'))
        if isindex:
            g = float("{0:.5f}".format(x))
    return g

app = Flask(__name__)

@app.route('/')
def test():
    description = 'nlgis2 API Service v.0.1<br>/api/maps (map polygons)<br>/api/data (data services)<br>'
    return description

@app.route('/demo')
def demo():
    sql = "select * from datasets.topics where 1=1";
    sql = sqlfilter(sql)
    return sql

@app.route('/progress')
def open():
    root = ''
    resp = make_response(render_template('progress.html', download=root))
    return resp

@app.route('/treemap')
def treemapweb():
    config = configuration()
    handle = ''
    switch = 'modern'
    if request.args.get('handle'):
        handle = request.args.get('handle')
    if request.args.get('historical'):
	switch = 'historical'
    config['remote'] = 'on'
    handles = []
    geodataset = ''
    # Geocoder
    if config['remote']:
        (classification, geodataset) = loaddataset_fromurl(config, config['geocoderhandle'])
    else:
        geodataset = loaddataset(handles)

    (modern, historical) = loadgeocoder(geodataset, 'geocoder')

    if switch == 'modern':
        activeindex = modern.index
        coder = modern
        class1 = switch
    else:
        activeindex = historical.index
        coder = historical
	class1 = switch

    # Loading dataset in dataframe
    handles = []
    handles.append(handle)
    try:
        if config['remote']:
            (class1, dataset) = loaddataset_fromurl(config, handle)
        else:
            dataset = loaddataset(handles)
    except:
	return 'No dataset ' + handle

    (cfilter, notint) = selectint(activeindex.values)
    (moderndata, historicaldata) = loadgeocoder(dataset, '')
    if switch == 'modern':
        maindata = moderndata
    else:
        maindata = historicaldata

    treemapdata = treemap(config, maindata, switch, cfilter, coder)
    return Response(treemapdata,  mimetype='application/json')

# Panel data
@app.route('/panel')
def panel():
    (handle, yearmin, yearmax, thisyear, ctrlist, lastyear) = ('', '1500', '2020', 1950, '', 2010)
    config = configuration()
    modern = moderncodes(config['modernnames'], config['apiroot'])
    if request.args.get('handle'):
        handle = str(request.args.get('handle'))
	handle = handle.replace(" ", "")
	handle = handle.replace("'", "")
    if request.args.get('dataset'):
        dataset = request.args.get('dataset')
    if request.args.get('ctrlist'):
        customcountrycodes = ''
        ctrlist = request.args.get('ctrlist')
    if request.args.get('year'):
        thisyear = request.args.get('year')

    jsonapi = config['apiroot'] + "/api/datasets?handle=" + str(handle)
    dataframe = load_api_data(jsonapi, '')
    
    result = ''
    ctrlimit = 10

    allcodes = {}
    panel = []
    names = {}

    for dataitem in dataframe:
        handle = dataitem['handle']
	try:
	    names[handle] = dataitem['title']
	except:
	    names[handle] = 'title'
	try:
            (dataset, codes) = paneldatafilter(dataitem['data'], int(yearmin), int(yearmax), ctrlist, handle)
	    if not dataset.empty:
                panel.append(dataset)
	except:
	    nodata = 0
	
    #return str(panel)
    if panel:
        totalpanel = pd.concat(panel)
        cleanedpanel = totalpanel.dropna(axis=1, how='any')
        cleanedpanel = totalpanel

        (header, data, countries, handles, vhandles) = panel2dict(cleanedpanel, names)  
	years = []
	for year in sorted(data):
            try:
        	years.append(int(year))
		lastyear = year
    	    except:
        	skip = 1

	# Return only years
	if request.args.get('showyears'):
	    yearsdata = {}
	    yearsdata['years'] = years
	    yearsdata['latestyear'] = lastyear
	    #yearsdata['data'] = data
	    yearsjson = json.dumps(yearsdata, ensure_ascii=False, sort_keys=True, indent=4)
	    return Response(yearsjson,  mimetype='application/json')

	# Show dataframe in CSV
        result = panel2csv(header, data, thisyear, countries, handles, vhandles, ctrlimit, modern)

    return Response(result,  mimetype='text/plain')

# Collabs
@app.route('/collabs')
def collabs():
    remove = ["date", "_id", "passwd"]
    (project, jsondata) = ('', '')
    data = {}
    if request.args.get('project'):
	project = request.args.get('project')
	data = readdata('projects', 'uri', project)
	for item in data:
    	    for r in remove:
		if item[r]:
                    del item[r]
	    jsondata = json.dumps(item, encoding="utf-8", sort_keys=True, indent=4)

    return Response(jsondata,  mimetype='application/json')

# Advanced statistiscs
@app.route('/advancedstats')
def advanced_statistics():
    (yearmin, yearmax, ctrlist) = (1500, 2020, '')
    config = configuration()
    handles = []

    if request.args.get('handle'):
        handledataset = request.args.get('handle')
	handledataset = handledataset.replace(" ", '')

    if request.args.get('dataset'):
        dataset = request.args.get('dataset')
        handles.append(dataset)

    if request.args.get('yearmin'):
        yearmin = request.args.get('yearmin')
    if request.args.get('yearmax'):
        yearmax = request.args.get('yearmax')
    if request.args.get('ctrlist'):
        ctrlist = request.args.get('ctrlist')

    modern = moderncodes(config['modernnames'], config['apiroot'])
    jsonapi = config['apiroot'] + '/api/datasets?handle=' + str(handledataset)

    (panel, cleanedpanel, names) = loadpanel(jsonapi, yearmin, yearmax, ctrlist)
    (header, data, countries, handles, vhandles) = advpanel2dict(cleanedpanel)

    ctrlimit = 200
    #result = panel2csv(header, data, thisyear, countries, handles, vhandles, ctrlimit, modern)
    #maindataframe = data2statistics(handles, cleanedpanel)
    #showhtml = statistics_tojson(maindataframe, modern)
    data = handle2statistics(handles, cleanedpanel)
    showhtml = statistics2table(data)
    return showhtml

# Dataverse API
@app.route('/download')
def download():
    (classification, pid, root) = ('', '', '')
    config = configuration()

    if request.args.get('pid'):
        pid = request.args.get('pid')
    if request.args.get('type[0]') == 'historical':
	classification = request.args.get('type[0]')	

    if classification:
	return 'historical'
    else:
        zipfile = downloadzip(pid)
        # CHANGE
        #return zipfile
        # DEBUG1
        root = config['apiroot'] + "/collabs/static/tmp/" + zipfile
        # HTML
        #resp = make_response(render_template('progress.html', download=root))
        #return "<a href=\"" + str(root) + "\">Download dataset(s) with all papers (zip archive)</a>"
        #return resp
        return redirect(root, code=301)

@app.route('/webmappercodes')
def webmapper():
    config = configuration()
    api = config['apiroot'] + "/collabs/static/data/historical.json"
    (regions, countries, ctr2reg, webmapper, geocoder) = histo(api)

    data = json.dumps(webmapper, encoding="utf-8", sort_keys=True, indent=4)
    return Response(data,  mimetype='application/json')

@app.route('/geocoder')
def geocoder():
    config = configuration()
    remote = 'on'

    # Geocoder
    handle = config['geocoderhandle']
    if remote:
        (classification, geodataset) = loaddataset_fromurl(config, handle)
    else:
        geodataset = loaddataset(handles)

    fromyear = 1500
    toyear = 2016
    cfilter = ''
    if request.args.get('name'):
        cfilter = request.args.get('name')
    if request.args.get('name'):
        cfilter = request.args.get('name')

    if fromyear:
        historical = ''
        if historical == 'old':
            api = config['apiroot'] + "/collabs/static/data/historical.json"
            (regions, countries, ctr2reg, webmapper, geocoder) = histo(api, cfilter)
	else:
	    geocoder = buildgeocoder(geodataset, config, cfilter)

    data = json.dumps(geocoder, encoding="utf-8", sort_keys=True, indent=4)
    return Response(data,  mimetype='application/json')

@app.route('/datasets')
def datasets():
    config = configuration()
    (jsondata, pid) = ('', '')
    handles = []
    combineddataset = []
    resultdataset = ''
    datainfo = []
    outformat = 'json'

    if request.args.get('format'):
        outformat = request.args.get('format')
    if request.args.get('handle'):
        pid = request.args.get('handle')
    if request.args.get('latest'):
	dataset = config['defaulthandle']
   	return dataset

    if pid:
        (handles, pidslist) = pidfrompanel(pid)

        hquery = formdatasetquery(handles,'')
        datainfo = readdatasets('datasets', json.loads(hquery))
	#if not datainfo:
	    #datainfo.append(pid)

        for dataset in datainfo:
	    data = {}
	    handle = dataset['handle']
	    if outformat == 'json':
                jsondata = str(dataset['data'])
	        jsondata = jsondata.replace(".0,", ",")
	        json_dict = ast.literal_eval(jsondata.strip())
	        data['handle'] = handle
	        try:
	            data['title'] = dataset['title']
	            data['units'] = dataset['units']
		    data['datasetID'] = dataset['datasetID']
	        except:
		    data['title'] = 'Title'
		    data['units'] = 'Units'
		    data['datasetID'] = 228
	        data['data'] = json_dict
	        combineddataset.append(data)
	    elif outformat == 'csv':
		data['data'] = dataset['csvframe']
		resultdataset = data['data']

    if outformat == 'json':
	if combineddataset:
            finaldata = json.dumps(combineddataset, encoding="utf-8", sort_keys=True, indent=4)
            return Response(finaldata,  mimetype='application/json')
    elif outformat == 'csv':
        return Response(resultdataset,  mimetype='text/plain')

@app.route('/dialog')
def dialog():
    pid = ''
    root = ''
    config = configuration()
    if request.args.get('pid'):
        pid = request.args.get('pid')
        zipfile = downloadzip(pid)
        root = config['clearance'] + "/collabs/static/tmp/" + zipfile

    resp = make_response(render_template('dialog.html', download=root))
    return resp

@app.route('/dataverse')
def dataverse():
    config = configuration()
    root = config['dataverseroot']
    query = ''
    if request.args.get('q'):
        query = request.args.get('q')
    apiurl = root + "/api/search?q=" + str(query) + "&key=" + config['key'] + "&type=dataset"
    url = request.url

    data = ''
    if query:
        rawdata = load_dataverse(apiurl)
    else:
        rawdata = simplesearch(root, url, config['apiroot'])
	#return rawdata

    try:
        data = json.dumps(rawdata, encoding="utf-8", sort_keys=True, indent=4)
	return Response(data,  mimetype='application/json')
    except:
	data = 'no data'
	return 'No data'

@app.route('/indicators')
def indicators():
    data = load_indicators("indicators.csv")
    return Response(data,  mimetype='application/json')

@app.route('/search')
def search():
    q = request.args.get('q')
    data = searchdata(q)
    return Response(data,  mimetype='application/json')

def load_province_data(apiurl, province):
    jsondataurl = apiurl + province
    
    req = urllib2.Request(jsondataurl)
    opener = urllib2.build_opener()
    f = opener.open(req)
    dataframe = simplejson.load(f)
    return dataframe

@app.route('/dataapi')
def dataapi():
    handles = []
    logscale = ''
    config = configuration()
    customyear = ''
    fromyear = '1500'
    toyear = '2012'
    categoriesMax = 6
    countriesNum = 200
    geocoder = ''
    (getrange, colormap, pallette, customcountrycodes) = ('', '', '', '')

    if request.args.get('logscale'):
        logscale = request.args.get('logscale')
    if request.args.get('year'):
        customyear = request.args.get('year')
    if request.args.get('catmax'):
        categoriesMax = int(request.args.get('catmax'))
    if request.args.get('getrange'):
        getrange = request.args.get('getrange')
    if request.args.get('colors'):
        pallette = request.args.get('colors')
    if request.args.get('colormap'):
        colormap = request.args.get('colormap')
    if request.args.get('geocoder'):
        geocoder = request.args.get('geocoder')
    if request.args.get('handle'):
        handlestring = request.args.get('handle')
	ishandle = re.search(r'(hdl:\d+\/\w+)', handlestring)
	if ishandle:
    	    handle = ishandle.group(1)
	    handle = handle.replace("'", "")
	else:
	    handle = handlestring
        handles.append(handle)

    if request.args.get('ctrlist'):
        customcountrycodes = ''
        tmpcustomcountrycodes = request.args.get('ctrlist')
        c = tmpcustomcountrycodes.split(',')
        for ids in sorted(c):
           if ids:
               customcountrycodes = str(customcountrycodes) + str(ids) + ','
        customcountrycodes = customcountrycodes[:-1]

    hist = {}
    config = configuration()
    try:
	if len(customcountrycodes):
            countriesNum = len(customcountrycodes.split(','))
            if countriesNum < categoriesMax:
	        if countriesNum >= 1:
                    categoriesMax = countriesNum
    except:
	nothing = 1

    (header, panelcells, codes, x1, x2, x3, x4, originalvalues) = data2panel(handles, customcountrycodes, fromyear, toyear, customyear, hist, logscale)

    modern = moderncodes(config['modernnames'], config['apiroot'])
    #jsondata = data2json(modern, codes, panelcells)
    #data = json.dumps(jsondata, ensure_ascii=False, sort_keys=True, indent=4)
    # SCALES
    (defaultcolor, colors) = getcolors(categoriesMax, pallette, colormap)
    (catlimit, ranges, dataset) = getscales(panelcells, colors, categoriesMax, geocoder, originalvalues, logscale)
 
    if getrange:
	(showrange, tmprange) = combinerange(ranges)
	webscale = webscales(showrange, colors, defaultcolor)
	data = json.dumps(webscale, ensure_ascii=False, sort_keys=True, indent=4)
	return Response(data,  mimetype='application/json')
    else:
        data = json.dumps(dataset, ensure_ascii=False, sort_keys=True, indent=4)
        return Response(data,  mimetype='application/json')

@app.route('/tabledata')
def tabledata():
    (data, aggrdata) = tableapi()
    return Response(data,  mimetype='text/plain')

if __name__ == '__main__':
    app.run()
