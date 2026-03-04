SCHEMA_CONTEXT = """I have a graph database containing musical linked data from various databases. As much of the information as possible is reconciled against Wikidata.

Please write me a SPARQL query to perform the following query:
<<USER_INPUT>>

When an entity is reconciled against Wikidata, wdt:P2888 is used to point to the reconciled Wikidata entity.
When an entity has a wdt:P31 triple, it contains information about the subclass that the entity is a part of (e.g. for mb:Artist, the wdt:P31 can point to human, musical group, etc).

The steps you should follow are:
1. Examine the ontology and extract the relevant parts.
2. Using that ontology, figure out which Q-IDs you need and perform web searches to find them.
3. Using the ontology and the Q-IDs, build the final SPARQL query.

Please follow these instructions:
- When asked to return a list of entities, please always return both the label (when available) and the URI for the entities.
- When finding Q-IDs to match against, search the web to get the best and most accurate results.
- Ensure that the Q-IDs that you've found are correct by performing another web search.
- Please scan all entities across all databases to find out which one(s) correspond to the query, and only select the relevant databases and entities.
- For any entity you search for within the LinkedMusic graph (not in Wikidata), please add a triple that uses the rdf:type property to explicitly verify its type.
- Do not use Wikidata to verify the type of entities, please instead use the LinkedMusic types, using the rdf:type property.
    - The only exception to this is when local entities have a wdt:P31 triple (like mb:Artist), then it is fine to check that triple using wdt:P31 in the local LinkedMusic graph, but never in a federated query.
- If you need data that is not located in the LinkedMusic graph, i.e. when there is no property for the information you need directly present in the ontology I give you, please use a federated query with Wikidata using the <https://query.wikidata.org/sparql> endpoint, but only do so if the information doesn't appear at all in the LinkedMusic graph ontology.
- Please ensure that you've fully reviewed the LinkedMusic ontology and extracted the relevant parts before performing federated queries.
- Please also double-check that you're not trying to use properties that do not appear in the ontology, unless they are a part of a federated query.
- When performing a federated query, ensure that the SPARQL query is efficient and will not create an unnecessarily high amount of requests.
- When resolving a Wikidata Q-ID, you must use the provided ontology to determine the linking path.
    - If a property's object is another defined class in the ontology (e.g., diamm:City wdt:P17 diamm:Country), your query must first navigate to that class and then use its wdt:P2888 property to get the Q-ID.
    - If a property's object is described by a literal string (e.g., ts:Session wdt:P17 "country"@en), you should assume the property links directly to the Wikidata URI.
- Once the SPARQL query is finalized, please re-read it and double-check that all QIDs are correct.
- For MusicBrainz, very few mb:Recording entities are reconciled against Wikidata since Wikidata does not carry information about specific recordings, only about the actual songs, so it's better to match reconciled data against mb:Work entities rather than mb:Recording

Please follow these constraints:
- Do not use string matching; instead check against Wikidata Q-IDs. The only exception to this is when the query explicitly requests finding entities based on text/string content (e.g., 'find tracks with X in the title', 'find artists whose names contain Y', 'search for works with Z in the description'). In such cases, use appropriate SPARQL string matching functions like CONTAINS(), REGEX(), or similar.
- Do not use the SELECT ... FROM syntax for named graphs. Please instead use the SELECT { GRAPH ... { ... } } syntax.
- Do not put any triples verifying the type of entities (using wdt:P31 or rdf:type) in federated query SERVICE blocks.
- Do not use Wikidata to retrieve labels unless directly asked to in the query. please prioritize as much as possible retrieving labels from the LinkedMusic database.
- Do not put any federated query SERVICE blocks inside a GRAPH block.
- Do not put any federated query SERVICE blocks inside an OPTIONAL block.
- Do not use a nested SELECT clause inside a SERVICE block.
- To avoid the Virtuoso error SP031, use a subquery before the SERVICE call for federated queries
- To avoid the Virtuoso error SP031, ensure every variable is assigned a value in a valid scope before it's used in a FILTER, BIND, or OPTIONAL block.

Please remember that the SPARQL query will not work, and you will have failed your task, if you do not follow these constraints and instructions. Please also be very diligent with your search for the correct Q-IDs, as they are one of the key parts of the SPARQL query.

Here are the 7 databases currently in LinkedMusic, and the IRIs for their RDF graphs:
- All triples for Cantus Database are stored in the <https://linkedmusic.ca/graphs/cantusdb/> graph, and their entity types use the `cdb:` prefix.
- All triples for DIAMM are stored in the <https://linkedmusic.ca/graphs/diamm/> graph, and their entity types use the `diamm:` prefix.
- All triples for Dig That Lick are stored in the <https://linkedmusic.ca/graphs/dig-that-lick/> graph, and their entity types use the `dtl:` prefix.
- All triples for The Session are stored in the <https://linkedmusic.ca/graphs/thesession/> graph, and their entity types use the `ts:` prefix.
- All triples for The Global Jukebox are stored in the <https://linkedmusic.ca/graphs/theglobaljukebox/> graph, and their entity types use the `gj:` prefix.
- All triples for MusicBrainz are stored in the <https://linkedmusic.ca/graphs/musicbrainz/> graph, and their entity types use the `mb:` prefix.
- All triples for RISM are stored in the <https://linkedmusic.ca/graphs/rism/> graph, and their entity types use the `rism:` prefix.

The following is a graph representation of the ontology of all the data in the database, for all 5 databases. Here is how to interpret this ontology:
- The subject are the LinkedMusic entity types (accessed using rdf:type)
- The predicates are the properties that those entities have
- The objects are described as below:
    - When the object is another class: If a property's object is another defined class in the ontology (e.g., diamm:City wdt:P17 diamm:Country), your query must first navigate to that diamm:Country class and then use its wdt:P2888 property to get the Q-ID.
    - When the object is a placeholder for an entity: If a property's object is a generic placeholder string that stands in for an entity's name (e.g., "country"@en, "instance of"@en, "performer"@en, "exact match"@en), assume the property in the actual graph links directly to a Wikidata URI.
    - When the object is a data value: If a property's object is a string that represents a data type (e.g., "publication date"@en, "coordinate location"@en, "label"), assume the property in the actual graph links to a literal value (a date, a string, coordinates, etc.) and not a Wikidata URI.
@prefix rdfs:	<http://www.w3.org/2000/01/rdf-schema#> .
@prefix wdt:	<http://www.wikidata.org/prop/direct/> .
@prefix skos:	<http://www.w3.org/2004/02/skos/core#> .
@prefix diamm:	<https://linkedmusic.ca/graphs/diamm/> .
@prefix ts:	<https://linkedmusic.ca/graphs/thesession/> .
@prefix mb:    <https://linkedmusic.ca/graphs/musicbrainz/> .
@prefix gj:	<https://linkedmusic.ca/graphs/theglobaljukebox/> .
@prefix dtl:	<https://linkedmusic.ca/graphs/dig-that-lick/> .
@prefix cdb:	<https://linkedmusic.ca/graphs/cantusdb/> .
@prefix rism:	<https://linkedmusic.ca/graphs/rism/> .

diamm:Composition
	rdfs:label	"label" ;
	wdt:P136	"genre" ;
	wdt:P361	diamm:Source ;
	wdt:P86	diamm:Person , "composer" .
diamm:Archive
	rdfs:label	"label" ;
	wdt:P11550	"RISM siglum" ;
	wdt:P131	diamm:City ;
	wdt:P2888	"exact match" ;
	wdt:P5504	"RISM ID" .
diamm:City
	rdfs:label	"label" ;
	wdt:P131	diamm:Region ;
	wdt:P17	diamm:Country ;
	wdt:P2888	"exact match" .
diamm:Country
	rdfs:label	"label" ;
	wdt:P2888	"exact match" .
diamm:Organization
	rdfs:label	"label" ;
	wdt:P131	diamm:City ;
	wdt:P17	diamm:Country ;
	wdt:P2888	"exact match" ;
	wdt:P1343	diamm:Source ;
	wdt:P31	"instance of" .
diamm:Person
	rdfs:label	"label" ;
	wdt:P2888	"exact match" ;
	wdt:P5504	"RISM ID" ;
	wdt:P1343	diamm:Source ;
	wdt:P214	"VIAF cluster ID" ;
	wdt:P569	"date of birth" ;
	wdt:P570	"date of death" ;
	skos:altLabel	"alt label" .
diamm:Region
	rdfs:label	"label" ;
	wdt:P17	diamm:Country ;
	wdt:P2888	"exact match" .
diamm:Set
	wdt:P217	"inventory number" ;
	wdt:P31	"instance of" .
diamm:Source
	rdfs:label	"label" ;
	wdt:P88	diamm:Organization , diamm:Person ;
	wdt:P131	diamm:City ;
	wdt:P361	diamm:Set ;
	wdt:P547	diamm:Person ;
	wdt:P941	diamm:Organization , diamm:Person ;
	wdt:P276	diamm:Archive , diamm:Organization ;
	wdt:P31	"instance of" ;
	wdt:P767	diamm:Person ;
	wdt:P123	diamm:Organization , diamm:Person ;
	wdt:P127	diamm:Organization , diamm:Person ;
	wdt:P825	diamm:Organization , diamm:Person ;
	wdt:P61	diamm:Person ;
	wdt:P11603	diamm:Person ;
	wdt:P1535	diamm:Organization , diamm:Person ;
	wdt:P2679	diamm:Person ;
	wdt:P859	diamm:Organization , diamm:Person ;
	wdt:P655	diamm:Person ;
	wdt:P1071	diamm:Organization ;
	wdt:P98	diamm:Person ;
	wdt:P50	diamm:Organization , diamm:Person ;
	wdt:P872	diamm:Person .

ts:Member
	rdfs:label	"label" .
ts:Session
	wdt:P131	"located in the administrative territorial entity" ;
	wdt:P17	"country" ;
	wdt:P276	"location" ;
	wdt:P625	"coordinate location" .
ts:Events
	rdfs:label	"label" ;
	wdt:P131	"located in the administrative territorial entity" ;
	wdt:P17	"country" ;
	wdt:P276	"location" ;
	wdt:P580	"start time" ;
	wdt:P582	"end time" ;
	wdt:P625	"coordinate location" .
ts:Tuneset
	wdt:P527	ts:Tune ;
	wdt:P170	ts:Member ;
	wdt:P571	"inception" .
ts:Tune
	rdfs:label	"label" ;
	skos:altLabel	"alt label" ;
	wdt:P747	ts:TuneSetting .
ts:TuneSetting
	wdt:P826	"tonality" ;
	wdt:P136	"genre" ;
	wdt:P3440	"time signature" .
ts:Recording
	rdfs:label	"label" ;
	wdt:P2888	"exact match" ;
	wdt:P175	"performer" ;
	wdt:P658	ts:Tune .

mb:Area
        rdfs:label        "label" ;
        wdt:P136        mb:Genre ;
        wdt:P2888        "exact match" ;
        wdt:P31        "instance of" ;
        wdt:P571        "inception" ;
        wdt:P576        "dissolved, abolished or demolished date" ;
        wdt:P131        mb:Area ;
        wdt:P85        mb:Work ;
        skos:altLabel        "alt label" .
mb:Artist
        rdfs:label        "label" ;
        wdt:P1066        mb:Artist ;
        wdt:P108        mb:Artist , mb:Label , mb:Place ;
        wdt:P123        mb:Label ;
        wdt:P127        mb:Place ;
        wdt:P1344        mb:Event ;
        wdt:P136        mb:Genre ;
        wdt:P138        mb:Artist , mb:Label , mb:Place , mb:ReleaseGroup , mb:Work ;
        wdt:P1416        mb:Place ;
        wdt:P21        "sex or gender" ;
        wdt:P26        mb:Artist ;
        wdt:P264        mb:Label ;
        wdt:P2652        mb:Artist ;
        wdt:P27        mb:Area ;
        wdt:P2888        "exact match" ;
        wdt:P31        "instance of" ;
        wdt:P3174        mb:Artist ;
        wdt:P3300        mb:Artist ;
        wdt:P3373        mb:Artist ;
        wdt:P361        mb:Artist , mb:Series ;
        wdt:P40        mb:Artist ;
        wdt:P451        mb:Artist ;
        wdt:P521        mb:Artist ;
        wdt:P527        mb:Artist ;
        wdt:P569        "date of birth" ;
        wdt:P570        "date of death" ;
        wdt:P571        "inception" ;
        wdt:P576        "dissolved, abolished or demolished date" ;
        wdt:P69        mb:Place ;
        wdt:P725        mb:Artist ;
        wdt:P742        mb:Artist ;
        wdt:P825        mb:Artist ;
        wdt:P8810        mb:Artist ;
        wdt:P972        mb:Series ;
        wdt:P57        mb:Place ;
        wdt:P19        mb:Area ;
        wdt:P20        mb:Area ;
        wdt:P740        mb:Area ;
        skos:altLabel        "alt label" .
mb:Event
        rdfs:label        "label" ;
        wdt:P136        mb:Genre ;
        wdt:P2888        "exact match" ;
        wdt:P31        "instance of" ;
        wdt:P3300        mb:Artist ;
        wdt:P527        mb:Event ;
        wdt:P1365        mb:Event ;
        wdt:P1366        mb:Event ;
        wdt:P110        mb:Artist ;
        wdt:P12484        mb:Artist ;
        wdt:P144        mb:Recording , mb:Release , mb:ReleaseGroup ;
        wdt:P170        mb:Artist ;
        wdt:P175        mb:Artist ;
        wdt:P179        mb:Series ;
        wdt:P2550        mb:ReleaseGroup ;
        wdt:P276        mb:Area , mb:Place ;
        wdt:P287        mb:Artist ;
        wdt:P371        mb:Artist ;
        wdt:P5028        mb:Artist ;
        wdt:P580        "start time" ;
        wdt:P582        "end time" ;
        wdt:P585        "point in time" ;
        wdt:P664        mb:Label ;
        wdt:P710        mb:Artist ;
        wdt:P915        mb:Recording ;
        skos:altLabel        "alt label" .
mb:Genre
        rdfs:label        "label" ;
        wdt:P138        mb:Artist , mb:Area , mb:Label , mb:Place , mb:ReleaseGroup ;
        wdt:P2888        "exact match" ;
        wdt:P495        mb:Area .
mb:Instrument
        rdfs:label        "label" ;
        wdt:P136        mb:Genre ;
        wdt:P2888        "exact match" ;
        wdt:P31        "instance of" ;
        wdt:P527        mb:Instrument ;
        wdt:P1531        mb:Instrument ;
        wdt:P155        mb:Instrument ;
        wdt:P156        mb:Instrument ;
        wdt:P279        mb:Instrument ;
        wdt:P61        mb:Artist , mb:Label ;
        wdt:P7084        mb:Instrument ;
        wdt:P495        mb:Area ;
        skos:altLabel        "alt label" .
mb:Label
        rdfs:label        "label" ;
        wdt:P127        mb:Artist ;
        wdt:P136        mb:Genre ;
        wdt:P138        mb:Work ;
        wdt:P2888        "exact match" ;
        wdt:P31        "instance of" ;
        wdt:P571        "inception" ;
        wdt:P576        "dissolved, abolished or demolished date" ;
        wdt:P112        mb:Artist ;
        wdt:P159        mb:Area ;
        wdt:P17        mb:Area ;
        wdt:P750        mb:Label ;
        wdt:P9237        mb:Label ;
        wdt:P1365        mb:Label ;
        wdt:P1366        mb:Label ;
        wdt:P355        mb:Label ;
        wdt:P749        mb:Label ;
        skos:altLabel        "alt label" .
mb:Place
        rdfs:label        "label" ;
        wdt:P127        mb:Artist , mb:Label ;
        wdt:P136        mb:Genre ;
        wdt:P138        mb:Artist ;
        wdt:P2888        "exact match" ;
        wdt:P31        "instance of" ;
        wdt:P361        mb:Place ;
        wdt:P527        mb:Place ;
        wdt:P571        "inception" ;
        wdt:P576        "dissolved, abolished or demolished date" ;
        wdt:P825        mb:Work ;
        wdt:P131        mb:Area ;
        wdt:P112        mb:Artist ;
        wdt:P1365        mb:Place ;
        wdt:P1366        mb:Place ;
        wdt:P915        mb:Recording ;
        wdt:P1037        mb:Artist ;
        wdt:P625        "coordinate location" ;
        wdt:P6375        "street address" ;
        skos:altLabel        "alt label" .
mb:Recording
        rdfs:label        "label" ;
        wdt:P123        mb:Label ;
        wdt:P136        mb:Genre ;
        wdt:P2888        "exact match" ;
        wdt:P3174        mb:Artist ;
        wdt:P3300        mb:Artist ;
        wdt:P361        mb:Recording ;
        wdt:P527        mb:Recording ;
        wdt:P57        mb:Artist ;
        wdt:P1071        mb:Area , mb:Place ;
        wdt:P10806        mb:Artist ;
        wdt:P12617        mb:Artist ;
        wdt:P161        mb:Artist ;
        wdt:P162        mb:Artist , mb:Label ;
        wdt:P1809        mb:Artist ;
        wdt:P2047        "duration" ;
        wdt:P272        mb:Label ;
        wdt:P3301        mb:Label ;
        wdt:P344        mb:Artist ;
        wdt:P3931        mb:Artist , mb:Label ;
        wdt:P4969        mb:Recording ;
        wdt:P5024        mb:Artist ;
        wdt:P5202        mb:Artist , mb:Label ;
        wdt:P5707        mb:Artist , mb:Recording , mb:Release ;
        wdt:P6275        mb:Artist ;
        wdt:P6718        mb:Recording ;
        wdt:P6942        mb:Artist ;
        wdt:P736        mb:Artist ;
        wdt:P767        mb:Artist ;
        wdt:P8546        mb:Area , mb:Place ;
        wdt:P943        mb:Artist ;
        wdt:P9767        mb:Recording ;
        wdt:P98        mb:Artist , mb:Label ;
        wdt:P9810        mb:Recording ;
        wdt:P110        mb:Artist ;
        wdt:P144        mb:Recording ;
        wdt:P175        mb:Artist ;
        wdt:P179        mb:Series ;
        wdt:P2550        mb:Work ;
        wdt:P287        mb:Artist ;
        wdt:P5028        mb:Artist ;
        wdt:P915        mb:Area , mb:Event , mb:Place ;
        wdt:P577        "publication date" ;
        skos:altLabel        "alt label" ;
        wdt:P870        mb:Instrument .
mb:Release
        rdfs:label        "label" ;
        wdt:P123        mb:Artist , mb:Label ;
        wdt:P136        mb:Genre ;
        wdt:P264        mb:Label ;
        wdt:P2888        "exact match" ;
        wdt:P31        "instance of" ;
        wdt:P3174        mb:Artist , mb:Label ;
        wdt:P3300        mb:Artist ;
        wdt:P361        mb:ReleaseGroup ;
        wdt:P57        mb:Artist ;
        wdt:P1534        "end cause" ;
        wdt:P655        mb:Artist ;
        wdt:P155        mb:Release ;
        wdt:P156        mb:Release ;
        wdt:P750        mb:Label ;
        wdt:P1071        mb:Area , mb:Place ;
        wdt:P10806        mb:Artist ;
        wdt:P162        mb:Artist ;
        wdt:P272        mb:Label ;
        wdt:P344        mb:Artist , mb:Label ;
        wdt:P3931        mb:Artist , mb:Label ;
        wdt:P5024        mb:Artist ;
        wdt:P5202        mb:Artist , mb:Label ;
        wdt:P5707        mb:Artist ;
        wdt:P6275        mb:Artist , mb:Label ;
        wdt:P767        mb:Artist ;
        wdt:P8546        mb:Area , mb:Place ;
        wdt:P943        mb:Artist ;
        wdt:P9767        mb:Release ;
        wdt:P98        mb:Artist , mb:Label ;
        wdt:P1365        mb:Release ;
        wdt:P1366        mb:Release ;
        wdt:P87        mb:Artist ;
        wdt:P110        mb:Artist , mb:Label ;
        wdt:P144        mb:Event ;
        wdt:P175        mb:Artist ;
        wdt:P287        mb:Artist , mb:Label ;
        wdt:P5028        mb:Artist ;
        wdt:P176        mb:Label ;
        wdt:P50        mb:Artist ;
        wdt:P577        "publication date" ;
        wdt:P629        mb:Release ;
        wdt:P658        mb:Recording ;
        wdt:P676        mb:Artist ;
        wdt:P86        mb:Artist ;
        wdt:P872        mb:Label ;
        wdt:P9813        "container" ;
        wdt:P495        mb:Area ;
        skos:altLabel        "alt label" ;
        wdt:P1081        mb:Area .
mb:ReleaseGroup
        rdfs:label        "label" ;
        wdt:P136        mb:Genre ;
        wdt:P2888        "exact match" ;
        wdt:P31        "instance of" ;
        wdt:P361        mb:ReleaseGroup ;
        wdt:P527        mb:ReleaseGroup ;
        wdt:P825        mb:Artist , mb:Label ;
        wdt:P12617        mb:Artist ;
        wdt:P9810        mb:ReleaseGroup ;
        wdt:P144        mb:Series , mb:ReleaseGroup ;
        wdt:P175        mb:Artist ;
        wdt:P179        mb:Series ;
        wdt:P2550        mb:ReleaseGroup ;
        wdt:P577        "publication date" ;
        wdt:P629        mb:ReleaseGroup ;
        wdt:P658        mb:ReleaseGroup ;
        skos:altLabel        "alt label" .
mb:Series
        rdfs:label        "label" ;
        wdt:P123        mb:Label ;
        wdt:P136        mb:Genre ;
        wdt:P138        mb:Artist , mb:ReleaseGroup ;
        wdt:P2888        "exact match" ;
        wdt:P31        "instance of" ;
        wdt:P361        mb:Series ;
        wdt:P527        mb:Series ;
        wdt:P112        mb:Artist ;
        wdt:P175        mb:Artist ;
        wdt:P179        mb:Release , mb:ReleaseGroup ;
        wdt:P276        mb:Area , mb:Place ;
        wdt:P50        mb:Artist ;
        skos:altLabel        "alt label" .
mb:Work
        rdfs:label        "label" ;
        wdt:P123        mb:Artist , mb:Label ;
        wdt:P136        mb:Genre ;
        wdt:P138        mb:Artist , mb:Work ;
        wdt:P2888        "exact match" ;
        wdt:P31        "instance of" ;
        wdt:P361        mb:Work ;
        wdt:P527        mb:Work ;
        wdt:P825        mb:Artist , mb:Area , mb:Label , mb:Place ;
        wdt:P655        mb:Artist ;
        wdt:P1071        mb:Area , mb:Place ;
        wdt:P10806        mb:Artist ;
        wdt:P4969        mb:Work ;
        wdt:P5202        mb:Artist ;
        wdt:P87        mb:Artist ;
        wdt:P144        mb:Work ;
        wdt:P179        mb:Series ;
        wdt:P50        mb:Artist ;
        wdt:P629        mb:Work ;
        wdt:P676        mb:Artist ;
        wdt:P86        mb:Artist ;
        wdt:P11849        mb:Artist ;
        skos:altLabel        "alt label" ;
        wdt:P1701        mb:Area ;
        wdt:P2567        mb:Artist ;
        wdt:P407        "language of work or name" ;
        wdt:P4647        mb:Area , mb:Event , mb:Place ;
        wdt:P5059        mb:Work ;
        wdt:P6166        mb:Work ;
        wdt:P826        "tonality" ;
        wdt:P8535        "tala" ;
        wdt:P8536        "raga" ;
        wdt:P88        mb:Artist , mb:Area , mb:Label , mb:Place , mb:Series .

gj:Culture
	rdfs:label	"label" ;
	wdt:P17	"country" ;
	wdt:P2888	"exact match" ;
	wdt:P361	"part of" ;
	wdt:P2341	"indigenous to" ;
	wdt:P2936	"language used" ;
	wdt:P4970	"alternative name" ;
	skos:altLabel	"alt label" .
gj:Ensemble
	wdt:P136	"genre" ;
	wdt:P870	"instrumentation" ;
	wdt:P2596	gj:Culture .
gj:Instrument
	rdfs:label	"label" ;
	wdt:P2888	"exact match" ;
	wdt:P2341	gj:Culture , "indigenous to" ;
	wdt:P248	"stated in" .
gj:Minutage
	rdfs:label	"label" ;
	wdt:P2596	gj:Culture ;
	wdt:P921	gj:Song .
gj:Parlametrics
	rdfs:label	"label" ;
	wdt:P407	"language of work or name" ;
	wdt:P31	"instance of" ;
	wdt:P585	"point in time" ;
	wdt:P8546	"recording location" ;
	wdt:P1840	"investigated by" .
gj:Phonotactics
	wdt:P921	gj:Song .
gj:Song
	rdfs:label	"label" ;
	wdt:P136	"genre" ;
	wdt:P585	"point in time" ;
	wdt:P175	"performer" ;
	wdt:P870	"instrumentation" ;
	wdt:P2341	"indigenous to" ;
	wdt:P2596	gj:Culture ;
	wdt:P495	"country of origin" ;
	wdt:P10893	"recordist" .
gj:Source
	rdfs:label	"label" ;
	wdt:P921	gj:Culture ;
	wdt:P577	"publication date" ;
	wdt:P50	"author" .

dtl:Solo
	wdt:P361	dtl:Track ;
	wdt:P175	"performer" ;
	wdt:P870	"instrumentation" .
dtl:Track
	rdfs:label	"label" ;
	wdt:P2888	"exact match" ;
	wdt:P361	"part of" ;
	wdt:P10135	"recording date" ;
	wdt:P175	"performer" ;
	wdt:P8546	"recording location" .

cdb:Source
	rdfs:label	"label" ;
	wdt:P276	"location" .
cdb:Chant
	rdfs:label	"label" ;
	wdt:P826	"tonality" ;
	wdt:P136	"genre" ;
	wdt:P361	cdb:Source ;
	wdt:P366	"has use" ;
	wdt:P837	"day in year for periodic occurrence" .

rism:Exemplar
	wdt:P86	rism:Person ;
	wdt:P276	rism:Institution ;
	wdt:P127	rism:Institution , rism:Person ;
	wdt:P825	rism:Institution , rism:Person ;
	wdt:P110	rism:Person ;
	wdt:P655	rism:Person ;
	wdt:P175	rism:Institution , rism:Person ;
	wdt:P5202	rism:Person ;
	wdt:P98	rism:Person ;
	wdt:P872	rism:Institution , rism:Person ;
	wdt:P6819	rism:Person .
rism:Incipit
	rdfs:label	"label" ;
	wdt:P2701	"file format" ;
	wdt:P3440	"time signature" .
rism:Source
	rdfs:label	"label" ;
	wdt:P5059	rism:Source ;
	wdt:P826	"tonality" ;
	wdt:P136	"genre" ;
	wdt:P361	rism:Source ;
	wdt:P86	rism:Institution , rism:Person ;
	wdt:P527	rism:Source ;
	wdt:P1922	rism:Incipit ;
	wdt:P276	rism:Institution ;
	wdt:P569	"date of birth" ;
	wdt:P570	"date of death" ;
	wdt:P767	rism:Person ;
	wdt:P123	rism:Institution , rism:Person ;
	wdt:P127	rism:Institution , rism:Person ;
	wdt:P825	rism:Institution , rism:Person ;
	wdt:P859	rism:Person ;
	wdt:P110	rism:Person ;
	wdt:P655	rism:Person ;
	wdt:P175	rism:Institution , rism:Person ;
	wdt:P1809	rism:Person ;
	wdt:P3931	rism:Institution , rism:Person ;
	wdt:P5202	rism:Person ;
	wdt:P98	rism:Institution , rism:Person ;
	wdt:P87	rism:Person ;
	wdt:P50	rism:Person ;
	wdt:P676	rism:Person ;
	wdt:P872	rism:Institution , rism:Person ;
	wdt:P750	rism:Institution , rism:Person ;
	wdt:P6819	rism:Institution , rism:Person ;
	wdt:P12328	rism:Source .
rism:Place
	rdfs:label	"label" .
rism:Subject
	rdfs:label	"label" ;
	wdt:P2888	"exact match" .
rism:Institution
	rdfs:label	"label" ;
	wdt:P2888	"exact match" .
rism:Person
	rdfs:label	"label" ;
	wdt:P2888	"exact match" ;
	wdt:P1038	rism:Person ;
	wdt:P26	rism:Person ;
	wdt:P3373	rism:Person ;
	wdt:P40	rism:Person ;
	wdt:P1889	rism:Person .

REMEMBER: Please find the correct QIDs
"""
