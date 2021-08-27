import time
import json
import requests
import urllib
import sys

d = open('omeka_credentials.json','r')
t = d.read()
d.close()

j = json.loads(t)

omeka_credentials = {
    'key_identity': j['key_identity'],
    'key_credential': j['key_credential'],
    'base_url':j['base_url'],
    'base_path':j['base_path']
}

base_url=j['base_url']
base_path=j['base_path']


#basic urllib constructor
def build_url(this_base_url, path='', args_dict={}):
	url_parts = list(urllib.parse.urlparse(this_base_url))
	url_parts[2] = base_path+path
	url_parts[4] = urllib.parse.urlencode(args_dict)
	return urllib.parse.urlunparse(url_parts)


#path is like '/omeka/api/resource_classes'
#args_dict is like:
## {term:'bibo:Note'}  OR, if coming from advanced search
## {'property[0][property]': 98, 'property[0][type]': 'ex', 'property[0][joiner]': 'and'}
## optional get_all parameter, if set to True, will fetch all results using Omeka API pagination functionality
def omeka_get(api_path,args_dict,retrieve_all=False):
	page=1
	
	all_results=[]
	while True:
		args_dict['page']=page
		this_url=build_url(base_url,api_path,args_dict)
		#print(this_url)
		response=requests.get(this_url,params=omeka_credentials)
		headers=response.headers
		j= json.loads(response.text)
		if type(j)==dict:
			j=[j]
		if len(j)==1 and page==1:
			all_results=j
			break
		elif len(j)>0:
			all_results += j
			page+=1
		else:
			break
		if retrieve_all==False:
			break
		#print('collected',len(all_results))
	return all_results

#retrieves json object for omeka classes,properties,or templates based on search parameters
#accepts basic key/value params on these native resources, e.g. ('resource_classes',{'term':'bibo:Note'})
#super simple but a little inflexible
#right now my searches are only working with equivalencies between key/value pairs
def basic_search(resource_type,args_dict={},retrieve_all=True):
	#print('searching',resource_type,args_dict)
	j=omeka_get(resource_type,args_dict,retrieve_all)
	return j


#advanced search args allow for some clever filters
#Right now it's super helpful for only grabbing items that have a specific property, which keeps me from having to iterate over all items looking for a value there
#e.g. advanced_args=[{'property_id':98,'operator':'ex'}]
#or advanced_args=[]
def advanced_search(resource_type=None,args_dict={},advanced_args=[],retrieve_all=True):
	
	p=0
	
	for arg in advanced_args:
		args_dict['property[%d][property]' %p]=arg['property_id']
	
		args_dict['property[%d][type]' %p]=arg['operator']
	
		#"ex" -- which is to say, "exists" does not require a value
		if arg['operator']!='ex':
			args_dict['property[%d][text]' %p]=arg['value']
	
		#for now, gonna hard-code in an "and" joiner between arguments
		args_dict['property[%d][joiner]' %p]='and'
		p+=1
	
	#print(args_dict)
	j=omeka_get(resource_type,args_dict,retrieve_all)
	
	return j



def upload_attachment(item_id,properties,fname):
	print("uploading",fname,"to item",item_id)
	data = {
	"o:ingester": "upload", 
	"file_index": "0", 
	"o:item": {"o:id": item_id},
	}
	#print('---with properties----',properties)
	new_properties_data=get_property_data(properties)
	#print(new_properties_data)
	for d in new_properties_data:
		data[d]=new_properties_data[d]
	headers = {
	'Content-type': 'application/json'
	}
	this_url=build_url(base_url,'media')
	#print(this_url)
	files = [('data', (None, json.dumps(data), 'application/json')),('file[0]', (fname, open(fname,'rb'),'image'))]
	#print("DATA ----------------\n",json.dumps(data),"\nEND DATA -------------------")
	#print("FILES ---------\n",files,"\nENDFILES------------")
	response = requests.post(this_url, params=omeka_credentials, files=files)
	print(response)

##"properties" data is key/value pairs, where the key is always a 
## [{'term': 'bibo:identifier', 'type': 'literal', 'value': '8W2R7WF5'}]
## the two optional arguments here, keep_nonlinks and keep_links, allow you to overwrite (keep...=False) or append (keep...=True) existing data of different types
def update_item(properties,item_id,keep_nonlinks=False,keep_links=True,endpoint='items'):
	#print(properties,item_id)
	item_data=basic_search(endpoint,args_dict={'id':item_id},retrieve_all=False)[0]
	new_properties_data=get_property_data(properties)
	headers = {'Content-type': 'application/json'}
	this_url=build_url(base_url,endpoint,{'id':item_id})
	#print(json.dumps(new_properties_data,indent=1))
	#print(json.dumps(item_data,indent=1))
	#print(item_data.keys())
	#print(new_properties_data.keys())
	for d in new_properties_data:
		
		if (keep_nonlinks==False and keep_links==False) or d not in item_data:
			item_data[d]=new_properties_data[d]
		
		else:
			rdfdata=[r for r in item_data[d] if 'type' in r]
			#print(rdfdata)
			for r in rdfdata:
				if (r['type']=='resource' and keep_links==False) or (((r['type'] in ['literal','uri']) or 'numeric' in r['type']) and keep_nonlinks==False):
					item_data[d].remove(r)
			if type(item_data[d])==list:
				item_data[d]+=new_properties_data[d]
			else:
				item_data[d]==new_properties_data[d]
			
	d=json.dumps(item_data)
	response = requests.patch(this_url, params=omeka_credentials, data=d, headers=headers)
	print(response)

def format_property_data(prop_type,prop_id,prop_value):
	#print(prop_type,prop_id,prop_value)
	if prop_type=='uri':
		prop_data={
			"type":prop_type,
			"property_id":prop_id,
			"@id":prop_value
		}
	elif prop_type=='literal' or 'numeric' in prop_type:
		prop_data={
			"type":prop_type,
			"property_id":prop_id,
			"@value":prop_value
		}
	elif prop_type=='resource':
		prop_data={
			"type":prop_type,
			"property_id":prop_id,
			"value_resource_id":prop_value
		}
	return prop_data

def get_property_data(properties):
	properties_dump={}
	for p in properties:
		#print(p)
		if type(p)==list:
			term=p[0]['term']
			property_id=basic_search('properties',{'term':term})[0]['o:id']
			prop_data=[]
			for prop_entry in p:
				prop_data.append(
					format_property_data(
						prop_entry['type'],
						property_id,
						prop_entry['value']
					)
				)
		else:
			term=p['term']
			property_id=basic_search('properties',{'term':term})[0]['o:id']
			prop_data=[
				format_property_data(
					p['type'],
					property_id,
					p['value']
				)
			]
		time.sleep(1)
		#print(prop_data)
		properties_dump[term]=prop_data
	return properties_dump

def create_item(properties,item_class=''):
	#print(properties)
	properties_dump=get_property_data(properties)

	resource_class_id=basic_search('resource_classes',{'term':item_class})[0]['o:id']
	
	item_data = {
		"@type": ["o:Item",item_class],
		"o:resource_class": 
				{
					"o:id": resource_class_id,
					"@id": build_url(base_url,'resource_classes/%d' %resource_class_id)
				}
	}
	
	for p in properties_dump:
		item_data[p]=properties_dump[p]	
	
	#print(json.dumps(item_data,indent=1))
	
	headers = {
	'Content-type': 'application/json'
	}
	
	url=build_url(base_url,'items')
	response = requests.post(url, params=omeka_credentials, data=json.dumps(item_data), headers=headers)
	j = json.loads(response.text)
	'''d=open("create.json",'w')
	d.write(json.dumps(item_data,indent=1))
	d.close()'''
	return j['o:id']
	
'''if __name__=="__main__":
	#create_item([{'term': 'dcterms:isPartOf', 'type': 'resource', 'value': 3758},{'term':'dcterms:title','type':'literal','value':'test'}])
	update_item([{'term': 'dcterms:isPartOf', 'type': 'resource', 'value': 3750}], 3762)'''
