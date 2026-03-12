# Schema corpus for the LangGraph agent's retrieve node.
#
# ONTOLOGY_CHUNKS: per-database ontology, selected by dict lookup on target_graphs.
# INSTRUCTION_CHUNKS: per-topic instruction text, selected by rule-based logic.
# VALID_DB_NAMES: ordered list of all known database keys.
#
# Source: extracted from app/llm/schema_context.py (which is kept unchanged for the
# fallback chain path).

ONTOLOGY_CHUNKS: dict[str, str] = {
    "diamm": """\
Database: DIAMM
Graph IRI: <https://linkedmusic.ca/graphs/diamm/>
Prefix: diamm: <https://linkedmusic.ca/graphs/diamm/>

Description: All triples for DIAMM are stored in the <https://linkedmusic.ca/graphs/diamm/>
graph. Digital Image Archive of Medieval Music. Contains compositions, sources (manuscripts),
archives, persons (composers), organizations, set, and geographic (city, region, country) entities. Entity types use the `diamm:` prefix.
QID linking: diamm:City, diamm:Country, diamm:Region, diamm:Archive, diamm:Person, and
diamm:Organization all have wdt:P2888 "exact match" for Wikidata reconciliation.
Cross-database: diamm:Archive and diamm:Person carry wdt:P5504 "RISM ID", which links
them to the corresponding rism:Institution and rism:Person entities in the RISM graph.

Ontology:
@prefix rdfs:  <http://www.w3.org/2000/01/rdf-schema#> .
@prefix wdt:   <http://www.wikidata.org/prop/direct/> .
@prefix wd:    <http://www.wikidata.org/entity/> .
@prefix skos:  <http://www.w3.org/2004/02/skos/core#> .
@prefix diamm: <https://linkedmusic.ca/graphs/diamm/> .

diamm:Composition
\trdfs:label\t"label" ;
\twdt:P136\t"genre" ;
\twdt:P361\tdiamm:Source ;
\twdt:P86\tdiamm:Person , "composer" .
diamm:Archive
\trdfs:label\t"label" ;
\twdt:P11550\t"RISM siglum" ;
\twdt:P131\tdiamm:City ;
\twdt:P2888\t"exact match" ;
\twdt:P5504\t"RISM ID" .
diamm:City
\trdfs:label\t"label" ;
\twdt:P131\tdiamm:Region ;
\twdt:P17\tdiamm:Country ;
\twdt:P2888\t"exact match" .
diamm:Country
\trdfs:label\t"label" ;
\twdt:P2888\t"exact match" .
diamm:Organization
\trdfs:label\t"label" ;
\twdt:P131\tdiamm:City ;
\twdt:P17\tdiamm:Country ;
\twdt:P2888\t"exact match" ;
\twdt:P1343\tdiamm:Source ;
\twdt:P31\t"instance of" .
diamm:Person
\trdfs:label\t"label" ;
\twdt:P2888\t"exact match" ;
\twdt:P5504\t"RISM ID" ;
\twdt:P1343\tdiamm:Source ;
\twdt:P214\t"VIAF cluster ID" ;
\twdt:P569\t"date of birth" ;
\twdt:P570\t"date of death" ;
\tskos:altLabel\t"alt label" .
diamm:Region
\trdfs:label\t"label" ;
\twdt:P17\tdiamm:Country ;
\twdt:P2888\t"exact match" .
diamm:Set
\twdt:P217\t"inventory number" ;
\twdt:P31\t"instance of" .
diamm:Source
\trdfs:label\t"label" ;
\twdt:P88\tdiamm:Organization , diamm:Person ;
\twdt:P131\tdiamm:City ;
\twdt:P361\tdiamm:Set ;
\twdt:P547\tdiamm:Person ;
\twdt:P941\tdiamm:Organization , diamm:Person ;
\twdt:P276\tdiamm:Archive , diamm:Organization ;
\twdt:P31\t"instance of" ;
\twdt:P767\tdiamm:Person ;
\twdt:P123\tdiamm:Organization , diamm:Person ;
\twdt:P127\tdiamm:Organization , diamm:Person ;
\twdt:P825\tdiamm:Organization , diamm:Person ;
\twdt:P61\tdiamm:Person ;
\twdt:P11603\tdiamm:Person ;
\twdt:P1535\tdiamm:Organization , diamm:Person ;
\twdt:P2679\tdiamm:Person ;
\twdt:P859\tdiamm:Organization , diamm:Person ;
\twdt:P655\tdiamm:Person ;
\twdt:P1071\tdiamm:Organization ;
\twdt:P98\tdiamm:Person ;
\twdt:P50\tdiamm:Organization , diamm:Person ;
\twdt:P872\tdiamm:Person .\
""",
    "thesession": """\
Database: The Session
Graph IRI: <https://linkedmusic.ca/graphs/thesession/>
Prefix: ts: <https://linkedmusic.ca/graphs/thesession/>

Description: All triples for The Session are stored in the
<https://linkedmusic.ca/graphs/thesession/> graph. Irish traditional music session
community database. Contains tunes, tune settings, recordings, sessions, and events.
Entity types use the `ts:` prefix.
IMPORTANT class distinction: ts:Session records a recurring session venue (location
data only, no date properties). ts:Events records a specific session occurrence on a
date. For any query asking when sessions happened or filtering by year/date, always use
ts:Events with wdt:P580 (start time) or wdt:P582 (end time) — NEVER ts:Session for
date filtering.
QID linking: ts:Recording has wdt:P2888 "exact match" for Wikidata reconciliation.
Cross-database: ts:Session and ts:Events link to Wikidata URIs directly via wdt:P17
(country) and wdt:P276 (location), enabling geographic correlation with other databases.
ts:Recording's wdt:P2888 can be correlated with matching entries in other LinkedMusic
databases through shared Wikidata QIDs.

Ontology:
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix wdt:  <http://www.wikidata.org/prop/direct/> .
@prefix wd:   <http://www.wikidata.org/entity/> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix ts:   <https://linkedmusic.ca/graphs/thesession/> .

ts:Member
\trdfs:label\t"label" .
ts:Session
\twdt:P131\t"located in the administrative territorial entity" ;
\twdt:P17\t"country" ;
\twdt:P276\t"location" ;
\twdt:P625\t"coordinate location" .
ts:Events
\trdfs:label\t"label" ;
\twdt:P131\t"located in the administrative territorial entity" ;
\twdt:P17\t"country" ;
\twdt:P276\t"location" ;
\twdt:P580\t"start time" ;
\twdt:P582\t"end time" ;
\twdt:P625\t"coordinate location" .
ts:Tuneset
\twdt:P527\tts:Tune ;
\twdt:P170\tts:Member ;
\twdt:P571\t"inception" .
ts:Tune
\trdfs:label\t"label" ;
\tskos:altLabel\t"alt label" ;
\twdt:P747\tts:TuneSetting .
ts:TuneSetting
\twdt:P826\t"tonality" ;
\twdt:P136\t"genre" ;
\twdt:P3440\t"time signature" .
ts:Recording
\trdfs:label\t"label" ;
\twdt:P2888\t"exact match" ;
\twdt:P175\t"performer" ;
\twdt:P658\tts:Tune .\
""",
    "musicbrainz": """\
Database: MusicBrainz
Graph IRI: <https://linkedmusic.ca/graphs/musicbrainz/>
Prefix: mb: <https://linkedmusic.ca/graphs/musicbrainz/>

Description: All triples for MusicBrainz are stored in the
<https://linkedmusic.ca/graphs/musicbrainz/> graph. Open music encyclopedia covering
artists, works, recordings, releases, labels, events, and places. Entity types use
the `mb:` prefix. Note: prefer mb:Work over mb:Recording for Wikidata reconciliation,
as very few mb:Recording entities have wdt:P2888 links.
QID linking: mb:Area, mb:Artist, mb:Event, mb:Genre, mb:Instrument, mb:Label, mb:Place,
mb:Recording, mb:Release, mb:ReleaseGroup, mb:Series, and mb:Work all have wdt:P2888
"exact match" for Wikidata reconciliation.
Cross-database: MusicBrainz has the broadest Wikidata coverage of all LinkedMusic
databases, enabling correlation with any other database whose entities also carry
wdt:P2888 through shared Wikidata QIDs.

Ontology:
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix wdt:  <http://www.wikidata.org/prop/direct/> .
@prefix wd:   <http://www.wikidata.org/entity/> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix mb:   <https://linkedmusic.ca/graphs/musicbrainz/> .

mb:Area
\trdfs:label\t"label" ;
\twdt:P136\tmb:Genre ;
\twdt:P2888\t"exact match" ;
\twdt:P31\t"instance of" ;
\twdt:P571\t"inception" ;
\twdt:P576\t"dissolved, abolished or demolished date" ;
\twdt:P131\tmb:Area ;
\twdt:P85\tmb:Work ;
\tskos:altLabel\t"alt label" .
mb:Artist
\trdfs:label\t"label" ;
\twdt:P1066\tmb:Artist ;
\twdt:P108\tmb:Artist , mb:Label , mb:Place ;
\twdt:P123\tmb:Label ;
\twdt:P127\tmb:Place ;
\twdt:P1344\tmb:Event ;
\twdt:P136\tmb:Genre ;
\twdt:P138\tmb:Artist , mb:Label , mb:Place , mb:ReleaseGroup , mb:Work ;
\twdt:P1416\tmb:Place ;
\twdt:P21\t"sex or gender" ;
\twdt:P26\tmb:Artist ;
\twdt:P264\tmb:Label ;
\twdt:P2652\tmb:Artist ;
\twdt:P27\tmb:Area ;
\twdt:P2888\t"exact match" ;
\twdt:P31\t"instance of" ;
\twdt:P3174\tmb:Artist ;
\twdt:P3300\tmb:Artist ;
\twdt:P3373\tmb:Artist ;
\twdt:P361\tmb:Artist , mb:Series ;
\twdt:P40\tmb:Artist ;
\twdt:P451\tmb:Artist ;
\twdt:P521\tmb:Artist ;
\twdt:P527\tmb:Artist ;
\twdt:P569\t"date of birth" ;
\twdt:P570\t"date of death" ;
\twdt:P571\t"inception" ;
\twdt:P576\t"dissolved, abolished or demolished date" ;
\twdt:P69\tmb:Place ;
\twdt:P725\tmb:Artist ;
\twdt:P742\tmb:Artist ;
\twdt:P825\tmb:Artist ;
\twdt:P8810\tmb:Artist ;
\twdt:P972\tmb:Series ;
\twdt:P57\tmb:Place ;
\twdt:P19\tmb:Area ;
\twdt:P20\tmb:Area ;
\twdt:P740\tmb:Area ;
\tskos:altLabel\t"alt label" .
mb:Event
\trdfs:label\t"label" ;
\twdt:P136\tmb:Genre ;
\twdt:P2888\t"exact match" ;
\twdt:P31\t"instance of" ;
\twdt:P3300\tmb:Artist ;
\twdt:P527\tmb:Event ;
\twdt:P1365\tmb:Event ;
\twdt:P1366\tmb:Event ;
\twdt:P110\tmb:Artist ;
\twdt:P12484\tmb:Artist ;
\twdt:P144\tmb:Recording , mb:Release , mb:ReleaseGroup ;
\twdt:P170\tmb:Artist ;
\twdt:P175\tmb:Artist ;
\twdt:P179\tmb:Series ;
\twdt:P2550\tmb:ReleaseGroup ;
\twdt:P276\tmb:Area , mb:Place ;
\twdt:P287\tmb:Artist ;
\twdt:P371\tmb:Artist ;
\twdt:P5028\tmb:Artist ;
\twdt:P580\t"start time" ;
\twdt:P582\t"end time" ;
\twdt:P585\t"point in time" ;
\twdt:P664\tmb:Label ;
\twdt:P710\tmb:Artist ;
\twdt:P915\tmb:Recording ;
\tskos:altLabel\t"alt label" .
mb:Genre
\trdfs:label\t"label" ;
\twdt:P138\tmb:Artist , mb:Area , mb:Label , mb:Place , mb:ReleaseGroup ;
\twdt:P2888\t"exact match" ;
\twdt:P495\tmb:Area .
mb:Instrument
\trdfs:label\t"label" ;
\twdt:P136\tmb:Genre ;
\twdt:P2888\t"exact match" ;
\twdt:P31\t"instance of" ;
\twdt:P527\tmb:Instrument ;
\twdt:P1531\tmb:Instrument ;
\twdt:P155\tmb:Instrument ;
\twdt:P156\tmb:Instrument ;
\twdt:P279\tmb:Instrument ;
\twdt:P61\tmb:Artist , mb:Label ;
\twdt:P7084\tmb:Instrument ;
\twdt:P495\tmb:Area ;
\tskos:altLabel\t"alt label" .
mb:Label
\trdfs:label\t"label" ;
\twdt:P127\tmb:Artist ;
\twdt:P136\tmb:Genre ;
\twdt:P138\tmb:Work ;
\twdt:P2888\t"exact match" ;
\twdt:P31\t"instance of" ;
\twdt:P571\t"inception" ;
\twdt:P576\t"dissolved, abolished or demolished date" ;
\twdt:P112\tmb:Artist ;
\twdt:P159\tmb:Area ;
\twdt:P17\tmb:Area ;
\twdt:P750\tmb:Label ;
\twdt:P9237\tmb:Label ;
\twdt:P1365\tmb:Label ;
\twdt:P1366\tmb:Label ;
\twdt:P355\tmb:Label ;
\twdt:P749\tmb:Label ;
\tskos:altLabel\t"alt label" .
mb:Place
\trdfs:label\t"label" ;
\twdt:P127\tmb:Artist , mb:Label ;
\twdt:P136\tmb:Genre ;
\twdt:P138\tmb:Artist ;
\twdt:P2888\t"exact match" ;
\twdt:P31\t"instance of" ;
\twdt:P361\tmb:Place ;
\twdt:P527\tmb:Place ;
\twdt:P571\t"inception" ;
\twdt:P576\t"dissolved, abolished or demolished date" ;
\twdt:P825\tmb:Work ;
\twdt:P131\tmb:Area ;
\twdt:P112\tmb:Artist ;
\twdt:P1365\tmb:Place ;
\twdt:P1366\tmb:Place ;
\twdt:P915\tmb:Recording ;
\twdt:P1037\tmb:Artist ;
\twdt:P625\t"coordinate location" ;
\twdt:P6375\t"street address" ;
\tskos:altLabel\t"alt label" .
mb:Recording
\trdfs:label\t"label" ;
\twdt:P123\tmb:Label ;
\twdt:P136\tmb:Genre ;
\twdt:P2888\t"exact match" ;
\twdt:P3174\tmb:Artist ;
\twdt:P3300\tmb:Artist ;
\twdt:P361\tmb:Recording ;
\twdt:P527\tmb:Recording ;
\twdt:P57\tmb:Artist ;
\twdt:P1071\tmb:Area , mb:Place ;
\twdt:P10806\tmb:Artist ;
\twdt:P12617\tmb:Artist ;
\twdt:P161\tmb:Artist ;
\twdt:P162\tmb:Artist , mb:Label ;
\twdt:P1809\tmb:Artist ;
\twdt:P2047\t"duration" ;
\twdt:P272\tmb:Label ;
\twdt:P3301\tmb:Label ;
\twdt:P344\tmb:Artist ;
\twdt:P3931\tmb:Artist , mb:Label ;
\twdt:P4969\tmb:Recording ;
\twdt:P5024\tmb:Artist ;
\twdt:P5202\tmb:Artist , mb:Label ;
\twdt:P5707\tmb:Artist , mb:Recording , mb:Release ;
\twdt:P6275\tmb:Artist ;
\twdt:P6718\tmb:Recording ;
\twdt:P6942\tmb:Artist ;
\twdt:P736\tmb:Artist ;
\twdt:P767\tmb:Artist ;
\twdt:P8546\tmb:Area , mb:Place ;
\twdt:P943\tmb:Artist ;
\twdt:P9767\tmb:Recording ;
\twdt:P98\tmb:Artist , mb:Label ;
\twdt:P9810\tmb:Recording ;
\twdt:P110\tmb:Artist ;
\twdt:P144\tmb:Recording ;
\twdt:P175\tmb:Artist ;
\twdt:P179\tmb:Series ;
\twdt:P2550\tmb:Work ;
\twdt:P287\tmb:Artist ;
\twdt:P5028\tmb:Artist ;
\twdt:P915\tmb:Area , mb:Event , mb:Place ;
\twdt:P577\t"publication date" ;
\tskos:altLabel\t"alt label" ;
\twdt:P870\tmb:Instrument .
mb:Release
\trdfs:label\t"label" ;
\twdt:P123\tmb:Artist , mb:Label ;
\twdt:P136\tmb:Genre ;
\twdt:P264\tmb:Label ;
\twdt:P2888\t"exact match" ;
\twdt:P31\t"instance of" ;
\twdt:P3174\tmb:Artist , mb:Label ;
\twdt:P3300\tmb:Artist ;
\twdt:P361\tmb:ReleaseGroup ;
\twdt:P57\tmb:Artist ;
\twdt:P1534\t"end cause" ;
\twdt:P655\tmb:Artist ;
\twdt:P155\tmb:Release ;
\twdt:P156\tmb:Release ;
\twdt:P750\tmb:Label ;
\twdt:P1071\tmb:Area , mb:Place ;
\twdt:P10806\tmb:Artist ;
\twdt:P162\tmb:Artist ;
\twdt:P272\tmb:Label ;
\twdt:P344\tmb:Artist , mb:Label ;
\twdt:P3931\tmb:Artist , mb:Label ;
\twdt:P5024\tmb:Artist ;
\twdt:P5202\tmb:Artist , mb:Label ;
\twdt:P5707\tmb:Artist ;
\twdt:P6275\tmb:Artist , mb:Label ;
\twdt:P767\tmb:Artist ;
\twdt:P8546\tmb:Area , mb:Place ;
\twdt:P943\tmb:Artist ;
\twdt:P9767\tmb:Release ;
\twdt:P98\tmb:Artist , mb:Label ;
\twdt:P1365\tmb:Release ;
\twdt:P1366\tmb:Release ;
\twdt:P87\tmb:Artist ;
\twdt:P110\tmb:Artist , mb:Label ;
\twdt:P144\tmb:Event ;
\twdt:P175\tmb:Artist ;
\twdt:P287\tmb:Artist , mb:Label ;
\twdt:P5028\tmb:Artist ;
\twdt:P176\tmb:Label ;
\twdt:P50\tmb:Artist ;
\twdt:P577\t"publication date" ;
\twdt:P629\tmb:Release ;
\twdt:P658\tmb:Recording ;
\twdt:P676\tmb:Artist ;
\twdt:P86\tmb:Artist ;
\twdt:P872\tmb:Label ;
\twdt:P9813\t"container" ;
\twdt:P495\tmb:Area ;
\tskos:altLabel\t"alt label" ;
\twdt:P1081\tmb:Area .
mb:ReleaseGroup
\trdfs:label\t"label" ;
\twdt:P136\tmb:Genre ;
\twdt:P2888\t"exact match" ;
\twdt:P31\t"instance of" ;
\twdt:P361\tmb:ReleaseGroup ;
\twdt:P527\tmb:ReleaseGroup ;
\twdt:P825\tmb:Artist , mb:Label ;
\twdt:P12617\tmb:Artist ;
\twdt:P9810\tmb:ReleaseGroup ;
\twdt:P144\tmb:Series , mb:ReleaseGroup ;
\twdt:P175\tmb:Artist ;
\twdt:P179\tmb:Series ;
\twdt:P2550\tmb:ReleaseGroup ;
\twdt:P577\t"publication date" ;
\twdt:P629\tmb:ReleaseGroup ;
\twdt:P658\tmb:ReleaseGroup ;
\tskos:altLabel\t"alt label" .
mb:Series
\trdfs:label\t"label" ;
\twdt:P123\tmb:Label ;
\twdt:P136\tmb:Genre ;
\twdt:P138\tmb:Artist , mb:ReleaseGroup ;
\twdt:P2888\t"exact match" ;
\twdt:P31\t"instance of" ;
\twdt:P361\tmb:Series ;
\twdt:P527\tmb:Series ;
\twdt:P112\tmb:Artist ;
\twdt:P175\tmb:Artist ;
\twdt:P179\tmb:Release , mb:ReleaseGroup ;
\twdt:P276\tmb:Area , mb:Place ;
\twdt:P50\tmb:Artist ;
\tskos:altLabel\t"alt label" .
mb:Work
\trdfs:label\t"label" ;
\twdt:P123\tmb:Artist , mb:Label ;
\twdt:P136\tmb:Genre ;
\twdt:P138\tmb:Artist , mb:Work ;
\twdt:P2888\t"exact match" ;
\twdt:P31\t"instance of" ;
\twdt:P361\tmb:Work ;
\twdt:P527\tmb:Work ;
\twdt:P825\tmb:Artist , mb:Area , mb:Label , mb:Place ;
\twdt:P655\tmb:Artist ;
\twdt:P1071\tmb:Area , mb:Place ;
\twdt:P10806\tmb:Artist ;
\twdt:P4969\tmb:Work ;
\twdt:P5202\tmb:Artist ;
\twdt:P87\tmb:Artist ;
\twdt:P144\tmb:Work ;
\twdt:P179\tmb:Series ;
\twdt:P50\tmb:Artist ;
\twdt:P629\tmb:Work ;
\twdt:P676\tmb:Artist ;
\twdt:P86\tmb:Artist ;
\twdt:P11849\tmb:Artist ;
\tskos:altLabel\t"alt label" ;
\twdt:P1701\tmb:Area ;
\twdt:P2567\tmb:Artist ;
\twdt:P407\t"language of work or name" ;
\twdt:P4647\tmb:Area , mb:Event , mb:Place ;
\twdt:P5059\tmb:Work ;
\twdt:P6166\tmb:Work ;
\twdt:P826\t"tonality" ;
\twdt:P8535\t"tala" ;
\twdt:P8536\t"raga" ;
\twdt:P88\tmb:Artist , mb:Area , mb:Label , mb:Place , mb:Series .\
""",
    "theglobaljukebox": """\
Database: The Global Jukebox
Graph IRI: <https://linkedmusic.ca/graphs/theglobaljukebox/>
Prefix: gj: <https://linkedmusic.ca/graphs/theglobaljukebox/>

Description: All triples for The Global Jukebox are stored in the
<https://linkedmusic.ca/graphs/theglobaljukebox/> graph. Cross-cultural music dataset
with songs, cultures, instruments, and ethnographic sources. Entity types use the `gj:` prefix.
QID linking: gj:Culture and gj:Instrument have wdt:P2888 "exact match" for Wikidata
reconciliation.
Cross-database: gj:Song links performers and countries of origin via Wikidata URIs
(wdt:P175 "performer", wdt:P495 "country of origin"), enabling correlation with artists
and regions in other LinkedMusic databases through shared Wikidata QIDs.

Ontology:
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix wdt:  <http://www.wikidata.org/prop/direct/> .
@prefix wd:   <http://www.wikidata.org/entity/> .
@prefix skos: <http://www.w3.org/2004/02/skos/core#> .
@prefix gj:   <https://linkedmusic.ca/graphs/theglobaljukebox/> .

gj:Culture
\trdfs:label\t"label" ;
\twdt:P17\t"country" ;
\twdt:P2888\t"exact match" ;
\twdt:P361\t"part of" ;
\twdt:P2341\t"indigenous to" ;
\twdt:P2936\t"language used" ;
\twdt:P4970\t"alternative name" ;
\tskos:altLabel\t"alt label" .
gj:Ensemble
\twdt:P136\t"genre" ;
\twdt:P870\t"instrumentation" ;
\twdt:P2596\tgj:Culture .
gj:Instrument
\trdfs:label\t"label" ;
\twdt:P2888\t"exact match" ;
\twdt:P2341\tgj:Culture , "indigenous to" ;
\twdt:P248\t"stated in" .
gj:Minutage
\trdfs:label\t"label" ;
\twdt:P2596\tgj:Culture ;
\twdt:P921\tgj:Song .
gj:Parlametrics
\trdfs:label\t"label" ;
\twdt:P407\t"language of work or name" ;
\twdt:P31\t"instance of" ;
\twdt:P585\t"point in time" ;
\twdt:P8546\t"recording location" ;
\twdt:P1840\t"investigated by" .
gj:Phonotactics
\twdt:P921\tgj:Song .
gj:Song
\trdfs:label\t"label" ;
\twdt:P136\t"genre" ;
\twdt:P585\t"point in time" ;
\twdt:P175\t"performer" ;
\twdt:P870\t"instrumentation" ;
\twdt:P2341\t"indigenous to" ;
\twdt:P2596\tgj:Culture ;
\twdt:P495\t"country of origin" ;
\twdt:P10893\t"recordist" .
gj:Source
\trdfs:label\t"label" ;
\twdt:P921\tgj:Culture ;
\twdt:P577\t"publication date" ;
\twdt:P50\t"author" .\
""",
    "digthatlick": """\
Database: Dig That Lick
Graph IRI: <https://linkedmusic.ca/graphs/dig-that-lick/>
Prefix: dtl: <https://linkedmusic.ca/graphs/dig-that-lick/>

Description: All triples for Dig That Lick are stored in the
<https://linkedmusic.ca/graphs/dig-that-lick/> graph. Jazz improvisation research
database containing tracks and melodic solos with performer and instrument metadata.
Entity types use the `dtl:` prefix.
QID linking: dtl:Track has wdt:P2888 "exact match" for Wikidata reconciliation.
IMPORTANT: wdt:P175 (performer) on dtl:Solo and dtl:Track, and wdt:P8546 (recording
location) on dtl:Track, store Wikidata entity URIs directly — NOT local LinkedMusic
entities. Use them directly (e.g. wdt:P175 wd:Q103767 for Charlie Parker,
wdt:P8546 wd:Q60 for NYC). Do NOT navigate via wdt:P2888 for these properties.
Cross-database: dtl:Solo links performers via wdt:P175 "performer" (Wikidata URI),
enabling correlation with artists in other LinkedMusic databases through shared Wikidata QIDs.

Ontology:
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix wdt:  <http://www.wikidata.org/prop/direct/> .
@prefix wd:   <http://www.wikidata.org/entity/> .
@prefix dtl:  <https://linkedmusic.ca/graphs/dig-that-lick/> .

dtl:Solo
\twdt:P361\tdtl:Track ;
\twdt:P175\twd: ;        # performer — Wikidata URI directly
\twdt:P870\t"instrumentation" .
dtl:Track
\trdfs:label\t"label" ;
\twdt:P2888\t"exact match" ;
\twdt:P361\t"part of" ;
\twdt:P10135\t"recording date" ;
\twdt:P175\twd: ;        # performer — Wikidata URI directly
\twdt:P8546\twd: .       # recording location — Wikidata URI directly\
""",
    "cantusdb": """\
Database: Cantus Database
Graph IRI: <https://linkedmusic.ca/graphs/cantusdb/>
Prefix: cdb: <https://linkedmusic.ca/graphs/cantusdb/>

Description: All triples for Cantus Database are stored in the
<https://linkedmusic.ca/graphs/cantusdb/> graph. Digital archive of medieval Latin
chant with sources (manuscripts) and individual chants annotated with genre, tonality,
and liturgical use. Entity types use the `cdb:` prefix.
QID linking: Cantus entities do not carry wdt:P2888 in the current ontology.
Cross-database: cdb:Source has wdt:P276 "location" (a Wikidata URI for the holding
institution's location), which is the only property linking Cantus to external entities.
Cross-database queries involving Cantus are limited to geographic location filtering.

Ontology:
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix wdt:  <http://www.wikidata.org/prop/direct/> .
@prefix wd:   <http://www.wikidata.org/entity/> .
@prefix cdb:  <https://linkedmusic.ca/graphs/cantusdb/> .

cdb:Source
\trdfs:label\t"label" ;
\twdt:P276\t"location" .
cdb:Chant
\trdfs:label\t"label" ;
\twdt:P826\t"tonality" ;
\twdt:P136\t"genre" ;
\twdt:P361\tcdb:Source ;
\twdt:P366\t"has use" ;
\twdt:P837\t"day in year for periodic occurrence" .\
""",
    "rism": """\
Database: RISM
Graph IRI: <https://linkedmusic.ca/graphs/rism/>
Prefix: rism: <https://linkedmusic.ca/graphs/rism/>

Description: All triples for RISM are stored in the <https://linkedmusic.ca/graphs/rism/>
graph. Répertoire International des Sources Musicales — global inventory of historical
music manuscripts and printed scores. Contains sources, exemplars (physical copies),
incipits, persons, institutions, and places. Entity types use the `rism:` prefix.
QID linking: rism:Institution, rism:Person, and rism:Subject carry wdt:P2888 "exact match"
for Wikidata reconciliation.
Cross-database: rism:Institution and rism:Person are directly referenced from DIAMM —
diamm:Archive and diamm:Person carry wdt:P5504 "RISM ID" linking to their corresponding
RISM counterparts. This is the only direct LinkedMusic-to-LinkedMusic join property
in the dataset.

Ontology:
@prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#> .
@prefix wdt:  <http://www.wikidata.org/prop/direct/> .
@prefix wd:   <http://www.wikidata.org/entity/> .
@prefix rism: <https://linkedmusic.ca/graphs/rism/> .

rism:Exemplar
\twdt:P86\trism:Person ;
\twdt:P276\trism:Institution ;
\twdt:P127\trism:Institution , rism:Person ;
\twdt:P825\trism:Institution , rism:Person ;
\twdt:P110\trism:Person ;
\twdt:P655\trism:Person ;
\twdt:P175\trism:Institution , rism:Person ;
\twdt:P5202\trism:Person ;
\twdt:P98\trism:Person ;
\twdt:P872\trism:Institution , rism:Person ;
\twdt:P6819\trism:Person .
rism:Incipit
\trdfs:label\t"label" ;
\twdt:P2701\t"file format" ;
\twdt:P3440\t"time signature" .
rism:Source
\trdfs:label\t"label" ;
\twdt:P5059\trism:Source ;
\twdt:P826\t"tonality" ;
\twdt:P136\t"genre" ;
\twdt:P361\trism:Source ;
\twdt:P86\trism:Institution , rism:Person ;
\twdt:P527\trism:Source ;
\twdt:P1922\trism:Incipit ;
\twdt:P276\trism:Institution ;
\twdt:P569\t"date of birth" ;
\twdt:P570\t"date of death" ;
\twdt:P767\trism:Person ;
\twdt:P123\trism:Institution , rism:Person ;
\twdt:P127\trism:Institution , rism:Person ;
\twdt:P825\trism:Institution , rism:Person ;
\twdt:P859\trism:Person ;
\twdt:P110\trism:Person ;
\twdt:P655\trism:Person ;
\twdt:P175\trism:Institution , rism:Person ;
\twdt:P1809\trism:Person ;
\twdt:P3931\trism:Institution , rism:Person ;
\twdt:P5202\trism:Person ;
\twdt:P98\trism:Institution , rism:Person ;
\twdt:P87\trism:Person ;
\twdt:P50\trism:Person ;
\twdt:P676\trism:Person ;
\twdt:P872\trism:Institution , rism:Person ;
\twdt:P750\trism:Institution , rism:Person ;
\twdt:P6819\trism:Institution , rism:Person ;
\twdt:P12328\trism:Source .
rism:Place
\trdfs:label\t"label" .
rism:Subject
\trdfs:label\t"label" ;
\twdt:P2888\t"exact match" .
rism:Institution
\trdfs:label\t"label" ;
\twdt:P2888\t"exact match" .
rism:Person
\trdfs:label\t"label" ;
\twdt:P2888\t"exact match" ;
\twdt:P1038\trism:Person ;
\twdt:P26\trism:Person ;
\twdt:P3373\trism:Person ;
\twdt:P40\trism:Person ;
\twdt:P1889\trism:Person .\
""",
}

INSTRUCTION_CHUNKS: dict[str, str] = {
    "named_graph_rules": """\
Named Graph Rules:
- Do not use the SELECT ... FROM syntax for named graphs.
- Always use the SELECT { GRAPH ... { ... } } syntax instead.
- Each database's triples live in its own named graph; always scope queries with GRAPH.\
""",
    "output_format_rules": """\
Output Format Rules:
- When asked to return a list of entities, always return both the label (when available)
  and the URI for the entities.
- For any entity searched within the LinkedMusic graph (not in Wikidata), add a triple
  using the rdf:type property to explicitly verify its type.
- Add a LIMIT clause to SELECT queries to avoid excessive results (e.g. LIMIT 100).
- Always declare PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#> at the top of the
  query whenever rdfs:label is used.\
""",
    "qid_resolution_rules": """\
QID Resolution Rules:
- When an entity is reconciled against Wikidata, wdt:P2888 is used to point to the
  reconciled Wikidata entity (exact match).
- The steps to follow when Q-IDs are needed:
  1. Examine the ontology and extract the relevant parts.
  2. Using that ontology, determine which Q-IDs are required and look them up via the
     wikidata_qid_lookup tool.
  3. Using the ontology and the Q-IDs, build the final SPARQL query.
  4. Once finalized, re-read the query and double-check that all Q-IDs are correct.
- When resolving a Wikidata Q-ID, use the ontology to determine the linking path:
  - If a property's object is another defined class in the ontology (e.g., diamm:City
    wdt:P17 diamm:Country), the query must first navigate to that diamm:Country class
    and then use its wdt:P2888 property to get the Q-ID.
  - If a property's object is a literal string placeholder (e.g., ts:Session wdt:P17
    "country"@en), assume the property in the actual graph links directly to a
    Wikidata URI.\
""",
    "federated_query_rules": """\
Federated Query Rules:
- Only use a federated query with Wikidata (<https://query.wikidata.org/sparql>) when
  the required information is not available at all in the LinkedMusic graph ontology.
- When performing a federated query, ensure the SPARQL is efficient (avoid Cartesian
  products; use a subquery to bind variables before the SERVICE block).
Constraints — violations will cause query failure:
- Do not put any triples verifying entity type (wdt:P31 or rdf:type) inside SERVICE blocks.
- Do not put any SERVICE blocks inside a GRAPH block.
- Do not put any SERVICE blocks inside an OPTIONAL block.
- Do not use a nested SELECT clause inside a SERVICE block.
- To avoid Virtuoso error SP031: use a subquery before the SERVICE call to pre-bind
  all variables that the SERVICE block will consume.
- To avoid Virtuoso error SP031: ensure every variable is assigned a value in valid
  scope before it is used in a FILTER, BIND, or OPTIONAL block.\
""",
    "entity_type_rules": """\
Entity Type Rules:
- For any entity searched within the LinkedMusic graph (not in Wikidata), add a triple
  using the rdf:type property to explicitly verify its type.
- Do not use Wikidata to verify the type of entities; use LinkedMusic types with rdf:type.
- Exception: when local entities have a wdt:P31 triple (like mb:Artist), it is
  acceptable to check that triple using wdt:P31 in the local LinkedMusic graph, but
  never inside a federated query SERVICE block.\
""",
    "string_matching_rules": """\
String Matching Rules:
- Default: do not use string matching. Check against Wikidata Q-IDs instead.
- Exception: when the query explicitly requests finding entities based on text or string
  content (e.g., "find tracks with X in the title", "find artists whose names contain Y",
  "search for works with Z in the description"), use appropriate SPARQL string functions:
  CONTAINS(), REGEX(), or similar.\
""",
    "musicbrainz_specific": """\
MusicBrainz-Specific Rules:
- Very few mb:Recording entities are reconciled against Wikidata, because Wikidata does
  not carry information about specific recordings — only about songs (works).
- Prefer matching reconciled data against mb:Work entities rather than mb:Recording
  when Wikidata Q-ID linking is required.\
""",
}

VALID_DB_NAMES: list[str] = list(ONTOLOGY_CHUNKS.keys())
