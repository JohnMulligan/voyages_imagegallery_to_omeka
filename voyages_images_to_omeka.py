import mysql.connector
import time
import json
import re
import requests
import omeka_interfacer as O
import os
#SO THE LOGIC HERE IS PRETTY STRAIGHTFORWARD
##I MAP THE OLD TABLES TO THE NEW TABLES
##WHERE POSSIBLE, I'VE DONE THIS IN A SINGLE COMMAND
##I HAVE RUN THIS LINE BY LINE WITH BASIC ERROR HANDLING & LOGGING
##I HAVE DROPPED DOUBLE-BIND FOREIGN KEYS, ALWAYS FAVORING THE TABLE THAT'S MORE CENTRAL (USUALLY, THIS SIMPLY MEANS THAT 'VOYAGES' KEEPS THE FK)
###SO NOW, FOR INSTANCE, YOU CAN ADD A SLAVESNUMNBERS ROW WITHOUT ATTACHING IT TO A VOYAGE
###BUT IT MAKES IMPORTATION POSSIBLE WITHOUT THE RIDICULOUS DANCE OF PURGING AND RE-APPLYING ALL FOREIGN KEYS, WHICH, OF COURSE, CAN OBSCURE ERRORS SUCH AS THE ABOVE
##I ALSO DECIDED TO DROP EXPLICIT ROWID PRIMARY KEYS FROM THE CONNECTION TABLES AND MAKE THEM EXPLICIT IN THE TABLES THEY CONNECT --E.G., ID MATCHES VOYAGE_ID IN THE VOYAGES TABLE IN ALL BUT ONE CASE. SO I COLLAPSED THESE.
###THIS WILL MAKE UPDATING THE DATABASE FROM WITHIN DJANGO MORE SEAMLESS
###BUT IT WILL ALSO REQUIRE THAT WHEN WE EXPORT AND REIMPORT, WE DO SO IN SUCH A WAY THAT THE PK'S ARE NOT AUTO-GENERATED AGAIN -- AS THAT WOULD CAUSE OUR VOYAGE_IDS TO DRIFT



d=open("dbcheckconf.json","r")
t=d.read()
d.close()
conf=json.loads(t)

cnx = mysql.connector.connect(**conf)
cursor = cnx.cursor()

property_map={
'title':['dcterms:title','literal'],
'description':['dcterms:description','literal'],
'creator':['dcterms:creator','literal'],
'language':['dcterms:language','literal'],
'date':['dcterms:date',"numeric:timestamp"],
'creator':['dcterms:creator','literal'],
'source':['dcterms:bibliographicCitation','literal'],
'category':['dcterms:type','literal'],
'file':['dcterms:identifier','literal'],
'voyage_id':['bibo:uri','uri']
}

#got to pull in category via category_id after the fake table join
#"ready_to_go" --> public. how to set this?
#"id","file","","","","","","ready_to_go","","","voyage_id"]

columns=["file","title","description","creator","language","source","date","category_id","voyage_id"]

cursor.execute("select %s from voyages.resources_image;" %','.join([i for i in columns]))
res=cursor.fetchall()
images_dict=[{columns[i.index(j)]:j for j in i} for i in res]

cursor.execute("select id,label from voyages.resources_imagecategory;")
res=cursor.fetchall()

imagecategorydict={i[0]:i[1] for i in res}


def format_properties(item,ignore_properties=[]):
	item_properties=[]
	for prop in item:
		if prop not in ignore_properties:
			prop_term,prop_type=property_map[prop]
			if type(item[prop])==list:
				this_prop=[]
				for p in item[prop]:
			
					this_prop.append({
							'term':prop_term,
							'type':prop_type,
							'value':p
						})
				item_properties.append(this_prop)
			else:
				item_properties.append([{
						'term':prop_term,
						'type':prop_type,
						'value':item[prop]
					}])
	return(item_properties)


def dl(uri,filename):
	print("fetching file %s" %filename)
	try:
		response=requests.get(uri)
		print(response)

		tmpfilename=re.sub("images/","",filename)
		open(tmpfilename,'wb').write(response.content)
		return tmpfilename
	except:
		return None



item_class='dctype:Image'

for i in images_dict:
	filename=i['file']
	uri="https://slavevoyages.org/documents/" +filename
	tmpfile=dl(uri,filename)
	if tmpfile:
		try:
			category=imagecategorydict[i['category_id']]
			property_dict=i
			#print(property_dict)
			del(property_dict['category_id'])
			property_dict['category']:category
			if property_dict['voyage_id']!='':
				property_dict['voyage_id']='https://slavevoyages.org/voyage/'+str(i['voyage_id'])+'/variables'
			item_properties=format_properties(property_dict,ignore_properties=[])
			omeka_id=O.create_item(item_properties,item_class)
			print("created omeka_id=%d" %(omeka_id))
			time.sleep(5)
			try:
				#print(tmpfile)
				O.upload_attachment(omeka_id,item_properties,tmpfile)
				os.remove(tmpfile)
			except:
				print("failed to upload %s to item %s" %(tmpfile,str(omeka_id)))
		except:
			print("failed to create item from %s" %uri)
			
			

	time.sleep(10)
