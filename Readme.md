# Omeka-S / Zotero Group Library sync

This will import items from Zotero into Omeka.

It tracks items with Zotero unique ID's.

It will maintain linking between child items (e.g., notes) and parent items (e.g., sources).

The first iteration won't deal with complex metadata beyond the item linking.

Ideally, it will also be more than a one-way importer, and will check against id's and timestamps in oder to prompt the user for updates from zotero based on more recent changes. This seems doable.

The Omeka interfacer python file already has a good start at using the Omeka-S advanced search API.



https://www.zotero.org/support/dev/web_api/v3/start

https://omeka.org/s/docs/developer/api/rest_api/

Was trying to do this by mapping the rdf vocabs automatically but it turns out that this requires some sort of hard-coding on both ends:
1. zotero side: Need to handle which of these items are class declarations, such as "foaf:person" wrapping author firstname/lastname tags, in order to properly import this data.
2. omeka side: Need to map data types (resource, literal, numeric (& numeric subtypes)) in order to make use of sorting & linking functionality in Omeka.


This is what I was going to use for rdf ontology mapping in zotero_format_items:

```
url=build_url(api_url,args_dict={'format':'rdf_dc'})
with urlopen(url) as f:
	tree = etree.parse(f, parser)
	for el in tree.iter():
		prefix=el.prefix
		lname=etree.QName(el.tag).localname
		try:
			val=int(el.text)
		except:
			val=el.text
		i[prefix+':'+lname]=val
```