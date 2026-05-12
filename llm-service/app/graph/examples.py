FEW_SHOT_EXAMPLES = [
    {
        "nl": "Find all songs in the UTSI database written by Stephen Foster",
        "sparql": """PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX utsi: <https://linkedmusic.ca/graphs/utsi/>
SELECT ?song
WHERE {
  GRAPH utsi: {
    ?song a utsi:Song .
    ?song wdt:P86 wd:Q305202
  }
}
LIMIT 100""",
    },
    # Challenge 1: find anything you can find via the databse's website
    {
        "nl": "Find all compositions in DIAMM that are composed by Guillaume de Machaut",
        "sparql": """PREFIX wd:    <http://www.wikidata.org/entity/>
PREFIX wdt:   <http://www.wikidata.org/prop/direct/>
PREFIX diamm: <https://linkedmusic.ca/graphs/diamm/>
SELECT ?composition
WHERE {
  GRAPH diamm: {
    ?composer wdt:P2888 wd:Q200580 .
    ?composition wdt:P86 ?composer .
  }
}""",
    },
    {
        "nl": "Find all sessions in France in The Session",
        "sparql": """PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX ts:   <https://linkedmusic.ca/graphs/thesession/>
SELECT ?session
WHERE {
  GRAPH ts: {
    ?session a ts:Session ;
             wdt:P17 wd:Q142 .
  }
}""",
    },
    {
        "nl": "Find all sessions in The Session that took place in 2015",
        "sparql": """PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX ts:   <https://linkedmusic.ca/graphs/thesession/>
SELECT ?event ?start
WHERE {
  GRAPH <https://linkedmusic.ca/graphs/thesession/> {
    ?event a ts:Events ;
           wdt:P580 ?start .
    FILTER (YEAR(?start) = 2015)
  }
}
LIMIT 100""",
    },
    {
        "nl": "Find all MusicBrainz recordings made by Taylor Swift",
        "sparql": """PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX mb:   <https://linkedmusic.ca/graphs/musicbrainz/>
SELECT ?recording
WHERE {
  GRAPH mb: {
    ?artist a mb:Artist .
    ?artist wdt:P2888 wd:Q26876 .
    ?recording a mb:Recording .
    ?recording wdt:P175 ?artist .
  }
}""",
    },
    {
        "nl": "Find all Ethiopian songs in The Global Jukebox",
        "sparql": """PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX gj:   <https://linkedmusic.ca/graphs/theglobaljukebox/>
SELECT ?song
WHERE {
  GRAPH gj: {
    ?song rdf:type gj:Song .
    ?song wdt:P495 wd:Q115 .
  }
}""",
    },
    {
        "nl": "Find all solos in Dig That Lick",
        "sparql": """PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX dtl:  <https://linkedmusic.ca/graphs/dig-that-lick/>
SELECT ?solo
WHERE {
  GRAPH dtl: {
    ?solo rdf:type dtl:Solo .
  }
}""",
    },
    {
        "nl": "Find all chants in Cantus DB in Lydian mode",
        "sparql": """PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX cdb:  <https://linkedmusic.ca/graphs/cantusdb/>
SELECT ?chant
WHERE {
  GRAPH cdb: {
    ?chant wdt:P826 wd:Q686115 .
  }
}""",
    },
    {
        "nl": "Find all sources in RISM held in the Bibliothèque nationale de France",
        "sparql": """PREFIX wd:    <http://www.wikidata.org/entity/>
PREFIX wdt:   <http://www.wikidata.org/prop/direct/>
PREFIX rism:  <https://linkedmusic.ca/graphs/rism/>
SELECT ?source
WHERE {
  GRAPH rism: {
    ?source wdt:P276 ?institution .
    ?institution wdt:P2888 wd:Q193563 .
  }
}""",
    },
    # Challenge 2: find anything you can find beyond what you can find on the website because you have a full access to the database
    {
        "nl": "Find all DIAMM archives and sort them by the number of sources they contain",
        "sparql": """PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX wdt:   <http://www.wikidata.org/prop/direct/>
PREFIX diamm: <https://linkedmusic.ca/graphs/diamm/>
SELECT ?archive (COUNT(?source) AS ?sourceCount)
WHERE {
  ?archive a diamm:Archive .
  OPTIONAL {
    ?source a diamm:Source ;
            wdt:P276 ?archive .
  }
}
GROUP BY ?archive
ORDER BY DESC(?sourceCount)""",
    },
    {
        "nl": "Find all the different time signatures for jigs in The Session",
        "sparql": """PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX ts:   <https://linkedmusic.ca/graphs/thesession/>
SELECT DISTINCT ?timeSignature
WHERE {
  ?tune a ts:Tune .
  ?tune wdt:P747 ?tuneSetting .
  ?tuneSetting wdt:P136 wd:Q1079270 .
  ?tuneSetting wdt:P3440 ?timeSignature .
}
ORDER BY ?timeSignature""",
    },
    {
        "nl": "Find all bands that share at least two members with Radiohead in MusicBrainz",
        "sparql": """PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX mb:   <https://linkedmusic.ca/graphs/musicbrainz/>
SELECT ?band (COUNT(DISTINCT ?sharedMember) AS ?sharedMemberCount)
WHERE {
  ?radiohead a mb:Artist ;
             wdt:P2888 wd:Q44190 .
  ?radiohead wdt:P527 ?radiomember .

  ?band a mb:Artist ;
        wdt:P527 ?radiomember ;
        wdt:P527 ?sharedMember .

  ?radiohead wdt:P527 ?sharedMember .
  FILTER(?band != ?radiohead)
}
GROUP BY ?band ?bandLabel
HAVING (COUNT(DISTINCT ?sharedMember) >= 2)
ORDER BY DESC(?sharedMemberCount)""",
    },
    {
        "nl": "Find all Global Jukebox cultures that have at least one song with flute instrumentation",
        "sparql": """PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX gj:   <https://linkedmusic.ca/graphs/theglobaljukebox/>
SELECT DISTINCT ?culture
WHERE {
  ?song a gj:Song .
  ?song wdt:P2596 ?culture .
  ?song wdt:P870 wd:Q11405 .
  ?culture a gj:Culture .
}""",
    },
    {
        "nl": "Find all tracks in Dig That Lick recorded in New York City",
        "sparql": """PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX dtl:  <https://linkedmusic.ca/graphs/dig-that-lick/>
SELECT DISTINCT ?track
WHERE {
  GRAPH dtl: {
    ?track a dtl:Track .
    ?track wdt:P8546 wd:Q60 .
  }
}""",
    },
    {
        "nl": "Find compositions by Mendelssohn in RISM written in 9/8 time",
        "sparql": """PREFIX wd:    <http://www.wikidata.org/entity/>
PREFIX wdt:   <http://www.wikidata.org/prop/direct/>
PREFIX rism:  <https://linkedmusic.ca/graphs/rism/>
SELECT ?source
WHERE {
  GRAPH rism: {
    ?source wdt:P86 ?mendelssohn .
    ?mendelssohn wdt:P2888 wd:Q46096 .
    ?source wdt:P1922 ?incipit .
    ?incipit wdt:P3440 "9/8" .
  }
}""",
    },
    # Challenge 3: find anything you can find with the database plus using the information in wikidata, e.g., the gender of the musician
    {
        "nl": "Find archives in DIAMM with an inception after 1900",
        "sparql": """PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX wd:    <http://www.wikidata.org/entity/>
PREFIX wdt:   <http://www.wikidata.org/prop/direct/>
PREFIX diamm: <https://linkedmusic.ca/graphs/diamm/>
SELECT DISTINCT ?archive
WHERE {
  GRAPH diamm: {
    ?archive a diamm:Archive ;
              wdt:P2888 ?archiveWikidata .
  }
  SERVICE <https://query.wikidata.org/sparql> {
    ?archiveWikidata wdt:P571 ?inceptionDate .
    FILTER (YEAR(?inceptionDate) > 1900)
  }
}""",
    },
    {
        "nl": "Find the capital city of the country with the most sessions",
        "sparql": """PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>
PREFIX wdt:   <http://www.wikidata.org/prop/direct/>
PREFIX ts:    <https://linkedmusic.ca/graphs/thesession/>
SELECT ?capitalCity ?capitalCityLabel
WHERE {
  {
    SELECT ?country (COUNT(?session) AS ?sessionCount)
    WHERE {
      GRAPH ts: {
        ?session a ts:Session .
        ?session wdt:P17 ?country .
      }
    }
    GROUP BY ?country
    ORDER BY DESC(?sessionCount)
    LIMIT 1
  }
  SERVICE <https://query.wikidata.org/sparql> {
    ?country wdt:P36 ?capitalCity .
    ?capitalCity rdfs:label ?capitalCityLabel .
    FILTER (LANG(?capitalCityLabel) = "en")
  }
}""",
    },
    {
        "nl": "What is the average number of record labels that female singers in MusicBrainz have signed with?",
        "sparql": """PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX mb:   <https://linkedmusic.ca/graphs/musicbrainz/>
SELECT (AVG(?labelCount) AS ?averageLabelsPerSinger)
WHERE {
  {
    SELECT ?artist (COUNT(DISTINCT ?label) AS ?labelCount)
    WHERE {
      GRAPH mb: {
        ?artist a mb:Artist .
        ?artist wdt:P2888 ?artistWikidata .
        ?artist wdt:P264 ?label .
        ?artist wdt:P21 wd:Q6581072 .
      }
      SERVICE <https://query.wikidata.org/sparql> {
        ?artistWikidata wdt:P106 wd:Q177220 .
      }
    }
    GROUP BY ?artist
  }
}""",
    },
    {
        "nl": "Find all Global Jukebox songs from Africa",
        "sparql": """PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX gj:   <https://linkedmusic.ca/graphs/theglobaljukebox/>
SELECT DISTINCT ?song
WHERE {
  GRAPH gj: {
    ?song a gj:Song .
    ?song wdt:P2596 ?culture .
    ?culture wdt:P17 ?country .
  }
  SERVICE <https://query.wikidata.org/sparql> {
    ?country wdt:P30 wd:Q15 .
  }
}""",
    },
    {
        "nl": "Find all solos Charlie Parker performed in New York City in Dig That Lick",
        "sparql": """PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX dtl:  <https://linkedmusic.ca/graphs/dig-that-lick/>
SELECT DISTINCT ?solo ?track
WHERE {
  GRAPH dtl: {
    ?solo rdf:type dtl:Solo ;
          wdt:P175 wd:Q103767 ;
          wdt:P361 ?track .
    ?track rdf:type dtl:Track ;
           wdt:P8546 wd:Q60 .
  }
}
ORDER BY ?solo
""",
    },
    {
        "nl": "Count how many solos were done by artists of each gender in Dig That Lick",
        "sparql": """PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX dtl:  <https://linkedmusic.ca/graphs/dig-that-lick/>
SELECT ?gender (COUNT(?solo) AS ?soloCount)
WHERE {
  GRAPH dtl: {
    ?solo a dtl:Solo ;
          wdt:P175 ?artist .
  }
  SERVICE <https://query.wikidata.org/sparql> {
    ?artist wdt:P21 ?gender .
  }
}
GROUP BY ?gender""",
    },
    {
        "nl": "Find composers in RISM who have siblings who are also composers in RISM",
        "sparql": """PREFIX wdt:   <http://www.wikidata.org/prop/direct/>
PREFIX rism:  <https://linkedmusic.ca/graphs/rism/>
SELECT DISTINCT ?composer
WHERE {
  GRAPH rism: {
    ?work wdt:P86 ?composer .
    ?composer wdt:P2888 ?wikicomposer .
  }
  SERVICE <https://query.wikidata.org/sparql> {
    ?wikisibling wdt:P3373 ?wikicomposer .
  }
  GRAPH rism: {
    ?sibling wdt:P2888 ?wikisibling .
    ?work2 wdt:P86 ?sibling .
  }
}""",
    },
    # Challenge : find anything across different databases and wikidata
    {
        "nl": "Find all songs in The Global Jukebox from countries with more than four sessions in The Session",
        "sparql": """PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX gj:   <https://linkedmusic.ca/graphs/theglobaljukebox/>
PREFIX ts:   <https://linkedmusic.ca/graphs/thesession/>
SELECT DISTINCT ?song
WHERE {
  GRAPH gj: {
    ?song a gj:Song ;
          wdt:P495 ?country .
  }
  GRAPH ts: {
    SELECT ?country (COUNT(DISTINCT ?session) AS ?sessionCount)
    WHERE {
      ?session a ts:Session ;
               wdt:P17 ?country .
    }
    GROUP BY ?country
    HAVING (COUNT(DISTINCT ?session) > 4)
  }
}""",
    },
    {
        "nl": "Find all works in MusicBrainz that, according to Dig That Lick, contain a solo performed by Charlie Parker",
        "sparql": """PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX mb:   <https://linkedmusic.ca/graphs/musicbrainz/>
PREFIX dtl:  <https://linkedmusic.ca/graphs/dig-that-lick/>
SELECT DISTINCT ?work
WHERE {
  GRAPH dtl: {
    ?solo a dtl:Solo ;
          wdt:P175 wd:Q103767 ;
          wdt:P361 ?track .
    ?track wdt:P2888 ?wikidataWork .
  }
  GRAPH mb: {
    ?work a mb:Work ;
          wdt:P2888 ?wikidataWork .
  }
}""",
    },
    {
        "nl": "Find all compositions or recordings with 'death' in the title",
        "sparql": """PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>
PREFIX mb:    <https://linkedmusic.ca/graphs/musicbrainz/>
PREFIX diamm: <https://linkedmusic.ca/graphs/diamm/>
PREFIX ts:    <https://linkedmusic.ca/graphs/thesession/>
PREFIX dtl:   <https://linkedmusic.ca/graphs/dig-that-lick/>
PREFIX gj:    <https://linkedmusic.ca/graphs/theglobaljukebox/>
SELECT DISTINCT ?entity ?label
WHERE {
  {
    GRAPH mb: {
      ?entity rdf:type mb:Work .
      ?entity rdfs:label ?label .
      FILTER (CONTAINS(LCASE(STR(?label)), "death"))
    }
  }
  UNION
  {
    GRAPH mb: {
      ?entity rdf:type mb:Recording .
      ?entity rdfs:label ?label .
      FILTER (CONTAINS(LCASE(STR(?label)), "death"))
    }
  }
  UNION
  {
    GRAPH diamm: {
      ?entity rdf:type diamm:Composition .
      ?entity rdfs:label ?label .
      FILTER (CONTAINS(LCASE(STR(?label)), "death"))
    }
  }
  UNION
  {
    GRAPH ts: {
      ?entity rdf:type ts:Recording .
      ?entity rdfs:label ?label .
      FILTER (CONTAINS(LCASE(STR(?label)), "death"))
    }
  }
  UNION
  {
    GRAPH dtl: {
      ?entity rdf:type dtl:Track .
      ?entity rdfs:label ?label .
      FILTER (CONTAINS(LCASE(STR(?label)), "death"))
    }
  }
  UNION
  {
    GRAPH ts: {
      ?entity rdf:type ts:Tune .
      ?entity rdfs:label ?label .
      FILTER (CONTAINS(LCASE(STR(?label)), "death"))
    }
  }
  UNION
  {
    GRAPH gj: {
      ?entity rdf:type gj:Song .
      ?entity rdfs:label ?label .
      FILTER (CONTAINS(LCASE(STR(?label)), "death"))
    }
  }
}""",
    },
    {
        "nl": "Find all musical instruments in the Global Jukebox featured in songs indigenous to Madagascar, and find recordings in MusicBrainz featuring these same instruments",
        "sparql": """PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX gj:   <https://linkedmusic.ca/graphs/theglobaljukebox/>
PREFIX mb:   <https://linkedmusic.ca/graphs/musicbrainz/>
SELECT DISTINCT ?wikidataInstrument ?recording
WHERE {
  GRAPH gj: {
    ?song wdt:P495 wd:Q1019 .
    ?song wdt:P870 ?wikidataInstrument .
  }
  GRAPH mb: {
    ?recording wdt:P870 ?musicBrainzInstrument .
    ?musicBrainzInstrument wdt:P2888 ?wikidataInstrument .
  }
}""",
    },
    {
        "nl": "Find all music events that happened on a day where at least one South Korean music label dissolved",
        "sparql": """PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX mb:   <https://linkedmusic.ca/graphs/musicbrainz/>
PREFIX ts:   <https://linkedmusic.ca/graphs/thesession/>
SELECT DISTINCT ?event
WHERE {
  GRAPH mb: {
    ?label a mb:Label ;
           wdt:P17 ?area ;
           wdt:P576 ?dissolutionDate .
    ?area wdt:P2888 wd:Q884 .
  }
  {
    GRAPH ts: {
      ?event a ts:Events ;
             wdt:P580 ?eventDate .
    }
  }
  UNION
  {
    GRAPH mb: {
      ?event a mb:Event ;
             wdt:P585 ?eventDate .
    }
  }
  FILTER (?eventDate = ?dissolutionDate)
}""",
    },
    {
        "nl": 'Find all chants in Cantus DB in Lydian mode.',
        "sparql": """PREFIX wd:  <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX cdb: <https://linkedmusic.ca/graphs/cantusdb/>
SELECT ?chant
WHERE {
  GRAPH cdb: {
    ?chant wdt:P826 wd:Q686115
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all chants in Cantus DB in Mixolydian mode.',
        "sparql": """PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX cdb:  <https://linkedmusic.ca/graphs/cantusdb/>
SELECT ?chant
WHERE {
  GRAPH cdb: {
    ?chant wdt:P826 wd:Q321814 .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all chants in Cantus DB for the feast of Saint Stephen.',
        "sparql": """PREFIX cdb: <https://linkedmusic.ca/graphs/cantusdb/>
SELECT ?chant
WHERE {
  GRAPH cdb: {
    ?chant wdt:P837 ?feast .
    FILTER(REGEX(STR(?feast), "stephan", "i"))
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all chants in Cantus Index associated with the feast of the Purification of Mary.',
        "sparql": """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX cantusindex: <https://linkedmusic.ca/graphs/cantusindex/>
SELECT ?chantID
WHERE {
  GRAPH cantusindex: {
    ?chantID wdt:P837 ?feast .
    FILTER(STR(?feast) = "Purificatio Mariae")
    ?chantID wdt:P6439 ?text
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all DIAMM manuscript sources held in Paris',
        "sparql": """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd:  <http://www.wikidata.org/entity/>
PREFIX diamm: <https://linkedmusic.ca/graphs/diamm/>
SELECT ?source
WHERE {
  GRAPH diamm: {
    ?source a diamm:Source ;
            wdt:P276 ?archive .
    ?archive wdt:P131 ?city .
    ?city wdt:P2888 wd:Q90 .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all solos in Dig That Lick.',
        "sparql": """PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX dtl: <https://linkedmusic.ca/graphs/dig-that-lick/>
SELECT ?solo
WHERE {
  GRAPH dtl: {
    ?solo rdf:type dtl:Solo
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all solos in Dig That Lick performed by Charlie Parker',
        "sparql": """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd:  <http://www.wikidata.org/entity/>
PREFIX dtl: <https://linkedmusic.ca/graphs/dig-that-lick/>
SELECT ?solo
WHERE {
  GRAPH dtl: {
    ?solo a dtl:Solo ;
          wdt:P175 wd:Q103767 .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all recordings in MusicBrainz by Miles Davis',
        "sparql": """PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX mb:   <https://linkedmusic.ca/graphs/musicbrainz/>
SELECT ?recording
WHERE {
  GRAPH mb: {
    ?artist a mb:Artist .
    ?artist wdt:P2888 wd:Q93341 .
    ?recording a mb:Recording .
    ?recording wdt:P175 ?artist .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all sources in RISM held at the British Library.',
        "sparql": """PREFIX wd:    <http://www.wikidata.org/entity/>
PREFIX wdt:   <http://www.wikidata.org/prop/direct/>
PREFIX rism:  <https://linkedmusic.ca/graphs/rism/>
SELECT ?source
WHERE {
  GRAPH rism: {
    ?source a rism:Source ;
        wdt:P276 ?institution .
    ?institution wdt:P2888 wd:Q23308 .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all compositions in SIMSSA DB by Josquin des Prez.',
        "sparql": """PREFIX wd:     <http://www.wikidata.org/entity/>
PREFIX wdt:    <http://www.wikidata.org/prop/direct/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
PREFIX simssa: <https://linkedmusic.ca/graphs/simssadb/>
SELECT ?work
WHERE {
  GRAPH simssa: {
    ?work a simssa:Work .
    ?work wdt:P86 ?composer . 
    ?composer wdt:P2888 wd:Q143100
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all works in SIMSSA DB composed by Tomás Luis de Victoria.',
        "sparql": """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd:  <http://www.wikidata.org/entity/>
PREFIX simssa: <https://linkedmusic.ca/graphs/simssadb/>
SELECT ?work
WHERE {
  GRAPH simssa: {
    ?work a simssa:Work ;
          wdt:P86 ?composer .
    ?composer wdt:P2888 wd:Q215128 .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all Ethiopian songs in The Global Jukebox.',
        "sparql": """PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX gj:   <https://linkedmusic.ca/graphs/theglobaljukebox/>
SELECT ?song
WHERE {
  GRAPH <https://linkedmusic.ca/graphs/theglobaljukebox/> {
    ?song a gj:Song .
    ?song wdt:P495 wd:Q115 .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all songs in the Global Jukebox that use guitar.',
        "sparql": """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd:  <http://www.wikidata.org/entity/>
PREFIX gj:  <https://linkedmusic.ca/graphs/theglobaljukebox/>
SELECT ?song
WHERE {
  GRAPH gj: {
    ?song a gj:Song ;
          wdt:P870 wd:Q6607 .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all sessions in France in The Session.',
        "sparql": """PREFIX wd:  <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX ts:  <https://linkedmusic.ca/graphs/thesession/>
SELECT ?session
WHERE {
  GRAPH ts: {
    ?session a ts:Session ;
             wdt:P17 wd:Q142 .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all sessions in Greece in The Session.',
        "sparql": """PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX ts:   <https://linkedmusic.ca/graphs/thesession/>
SELECT ?session
WHERE {
  GRAPH ts: {
    ?session a ts:Session ;
             wdt:P17 wd:Q41 .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all sessions in The Session held in Ireland.',
        "sparql": """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd:  <http://www.wikidata.org/entity/>
PREFIX ts:  <https://linkedmusic.ca/graphs/thesession/>
SELECT ?session
WHERE {
  GRAPH ts: {
    ?session a ts:Session ;
             wdt:P17 wd:Q27 .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all songs in the University of Tennessee Song Index composed by George Gershwin.',
        "sparql": """PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX utsi: <https://linkedmusic.ca/graphs/utsi/>
SELECT ?song
WHERE {
  GRAPH utsi: {
    ?song a utsi:Song .
    ?song wdt:P86 wd:Q123829
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all solos in Weimar Jazz Database featuring clarinet.',
        "sparql": """PREFIX wd:     <http://www.wikidata.org/entity/>
PREFIX wdt:    <http://www.wikidata.org/prop/direct/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
PREFIX wjazzd: <https://linkedmusic.ca/graphs/wjazzd/>
SELECT ?solo
WHERE {
  GRAPH wjazzd: {
    ?solo a wjazzd:Solo .
    ?solo wdt:P870 wd:Q8343
  }
}
LIMIT 100""",
    },
    {
        "nl": 'What is the average number of chants per source in Cantus DB?',
        "sparql": """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX cdb: <https://linkedmusic.ca/graphs/cantusdb/>
SELECT (AVG(?chantCount) AS ?avgChantsPerSource)
WHERE {
  {
    SELECT ?source (COUNT(?chant) AS ?chantCount)
    WHERE {
      GRAPH cdb: {
        ?chant wdt:P361 ?source .
      }
    }
    GROUP BY ?source
  }
}
LIMIT 100""",
    },
    {
        "nl": 'How many chants are there for each mode in Cantus DB?',
        "sparql": """PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX cdb:  <https://linkedmusic.ca/graphs/cantusdb/>
SELECT ?mode (COUNT(?chant) AS ?chantCount)
WHERE {
  GRAPH cdb: {
    ?chant wdt:P826 ?mode .
  }
}
GROUP BY ?mode
ORDER BY DESC(?chantCount)
LIMIT 100""",
    },
    {
        "nl": 'What are the top 10 most common liturgical uses (offices) in Cantus DB by number of chants?',
        "sparql": """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX cdb: <https://linkedmusic.ca/graphs/cantusdb/>
SELECT ?office (COUNT(?chant) AS ?chantCount)
WHERE {
  GRAPH cdb: {
    ?chant wdt:P366 ?office .
  }
}
GROUP BY ?office
ORDER BY DESC(?chantCount)
LIMIT 10""",
    },
    {
        "nl": 'How many chants are there in Cantus Index for each feast?',
        "sparql": """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX cantusindex: <https://linkedmusic.ca/graphs/cantusindex/>
SELECT ?feast (COUNT(?chant) AS ?count)
WHERE {
  GRAPH cantusindex: {
    ?chant a cantusindex:Chant .
    ?chant wdt:P837 ?feast .
  }
}
GROUP BY ?feast
ORDER BY DESC(?count)
LIMIT 100""",
    },
    {
        "nl": 'How many chants in Cantus Index are written in each language?',
        "sparql": """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX cantusindex: <https://linkedmusic.ca/graphs/cantusindex/>
SELECT ?language (COUNT(?chant) AS ?chantCount)
WHERE {
  GRAPH cantusindex: {
    ?chant a cantusindex:Chant ;
           wdt:P407 ?language .
  }
}
GROUP BY ?language
ORDER BY DESC(?chantCount)
LIMIT 100""",
    },
    {
        "nl": 'Find all DIAMM archives and list the number of sources that they contain.',
        "sparql": """PREFIX wdt:   <http://www.wikidata.org/prop/direct/>
PREFIX diamm: <https://linkedmusic.ca/graphs/diamm/>
SELECT ?archive (COUNT(?source) AS ?sourceCount)
WHERE {
  GRAPH diamm: {
    ?archive a diamm:Archive .
    ?source a diamm:Source .
    ?source wdt:P276 ?archive .
  }
}
GROUP BY ?archive
ORDER BY DESC(?sourceCount)
LIMIT 100""",
    },
    {
        "nl": 'Find all DIAMM compositions that do not have a genre assigned.',
        "sparql": """PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>
PREFIX wdt:   <http://www.wikidata.org/prop/direct/>
PREFIX diamm: <https://linkedmusic.ca/graphs/diamm/>
SELECT ?composition
WHERE {
  GRAPH diamm: {
    ?composition a diamm:Composition .
    FILTER NOT EXISTS {
      ?composition wdt:P136 ?genre .
    }
  }
}
LIMIT 100""",
    },
    {
        "nl": "Find all DIAMM persons whose name contains 'Bach'.",
        "sparql": """PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>
PREFIX diamm: <https://linkedmusic.ca/graphs/diamm/>
SELECT ?person
WHERE {
  GRAPH diamm: {
    ?person a diamm:Person .
    FILTER (CONTAINS(LCASE(STR(?personLabel)), "bach"))
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all tracks in Dig That Lick recorded in New York City.',
        "sparql": """PREFIX wd:  <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX dtl: <https://linkedmusic.ca/graphs/dig-that-lick/>
SELECT DISTINCT ?track
WHERE {
  GRAPH dtl: {
    ?track a dtl:Track .
    ?track wdt:P8546 wd:Q60 .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'How many solos does each track in Dig That Lick contain?',
        "sparql": """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX dtl: <https://linkedmusic.ca/graphs/dig-that-lick/>
SELECT ?track (COUNT(?solo) AS ?soloCount)
WHERE {
  GRAPH dtl: {
    ?solo a dtl:Solo ;
          wdt:P361 ?track .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'What are the top 10 cities where the most jazz solos were recorded in Dig That Lick? List the city and the number of solos.',
        "sparql": """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX dtl: <https://linkedmusic.ca/graphs/dig-that-lick/>
SELECT ?location (COUNT(?solo) AS ?soloCount)
WHERE {
  GRAPH dtl: {
    ?solo a dtl:Solo ;
          wdt:P361 ?track .
    ?track wdt:P8546 ?location .
  }
}
GROUP BY ?location
ORDER BY DESC(?soloCount)
LIMIT 10""",
    },
    {
        "nl": 'Find all bands that share at least two members with Radiohead in MusicBrainz.',
        "sparql": """PREFIX wd:  <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX mb:  <https://linkedmusic.ca/graphs/musicbrainz/>

SELECT DISTINCT ?band
WHERE {
  GRAPH mb: {
    ?radiohead a mb:Artist ;
               wdt:P2888 wd:Q44190 .
    ?radiohead wdt:P527 ?radiomember .
    ?band a mb:Artist ;
          wdt:P527 ?radiomember ;
          wdt:P527 ?sharedMember .
    ?radiohead wdt:P527 ?sharedMember .
    FILTER(?band != ?radiohead)
  }
}
GROUP BY ?band
HAVING (COUNT(DISTINCT ?sharedMember) >= 2)""",
    },
    {
        "nl": 'Find all MusicBrainz artists born on January 1st.',
        "sparql": """PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX mb:   <https://linkedmusic.ca/graphs/musicbrainz/>

SELECT ?artist ?birthDate
WHERE {
  GRAPH mb: {
    ?artist a mb:Artist ;
            wdt:P569 ?birthDate .
    FILTER(REGEX(STR(?birthDate), "-01-01"))
  }
}
LIMIT 100""",
    },
    {
        "nl": 'How many recordings are there in MusicBrainz for each genre?',
        "sparql": """PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX mb:   <https://linkedmusic.ca/graphs/musicbrainz/>
SELECT ?genre (COUNT(?recording) AS ?recordingCount)
WHERE {
  GRAPH mb: {
    ?recording a mb:Recording .
    ?recording wdt:P136 ?genre .
  }
}
GROUP BY ?genre
ORDER BY DESC(?recordingCount)
LIMIT 100""",
    },
    {
        "nl": 'Which RISM composers have more than 50 sources attributed to them?',
        "sparql": """PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-making#>
PREFIX wdt:   <http://www.wikidata.org/prop/direct/>
PREFIX rism:  <https://linkedmusic.ca/graphs/rism/>

SELECT ?composer
WHERE {
  GRAPH rism: {
    ?composer a rism:Person .
    ?source wdt:P86 ?composer .
    FILTER NOT EXISTS { ?composer rdfs:label ?composerLabel }
  }
}
GROUP BY ?composer
HAVING (COUNT(?source) > 50)
ORDER BY ?composer
LIMIT 100""",
    },
    {
        "nl": 'What are the top 10 most common keys used in RISM sources?',
        "sparql": """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX rism: <https://linkedmusic.ca/graphs/rism/>

SELECT ?key
WHERE {
  GRAPH rism: {
    ?source a rism:Source .
    ?source wdt:P826 ?key .
  }
}
GROUP BY ?key
ORDER BY DESC(COUNT(?source))
LIMIT 10""",
    },
    {
        "nl": "Find all RISM sources whose title contains the word 'sonata'.",
        "sparql": """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rism: <https://linkedmusic.ca/graphs/rism/>
SELECT ?source
WHERE {
  GRAPH rism: {
    ?source a rism:Source ;
            rdfs:label ?label .
    FILTER(CONTAINS(LCASE(STR(?label)), "sonata"))
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Which musical works in SIMSSA DB have at least two associated files?',
        "sparql": """PREFIX wdt:    <http://www.wikidata.org/prop/direct/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
PREFIX simssa: <https://linkedmusic.ca/graphs/simssadb/>
SELECT ?work
WHERE {
  GRAPH simssa: {
    ?file a simssa:File ;
          wdt:P6243 ?work .

    ?work a simssa:Work .
  }
}
GROUP BY ?work
HAVING (COUNT(?file) >= 2)
LIMIT 100""",
    },
    {
        "nl": 'Which composers in SIMSSA DB have composed more than two works?',
        "sparql": """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX simssa: <https://linkedmusic.ca/graphs/simssadb/>

SELECT ?composer
WHERE {
  GRAPH simssa: {
    ?work a simssa:Work ;
          wdt:P86 ?composer .
  }
}
GROUP BY ?composer
HAVING (COUNT(?work) > 2)
LIMIT 100""",
    },
    {
        "nl": 'Find all Global Jukebox cultures that have at least one song with flute instrumentation.',
        "sparql": """PREFIX wd:  <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX gj:  <https://linkedmusic.ca/graphs/theglobaljukebox/>
SELECT DISTINCT ?culture
WHERE {
  GRAPH gj: {
    ?song a gj:Song .
    ?song wdt:P2596 ?culture .
    ?song wdt:P870 wd:Q11405 .
    ?culture a gj:Culture .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Which Global Jukebox cultures have more than 10 songs?',
        "sparql": """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX gj: <https://linkedmusic.ca/graphs/theglobaljukebox/>

SELECT ?culture
WHERE {
  GRAPH gj: {
    ?song a gj:Song ;
          wdt:P2596 ?culture .
    ?culture a gj:Culture .
  }
}
GROUP BY ?culture
HAVING (COUNT(?song) > 10)
LIMIT 100""",
    },
    {
        "nl": "Find all tunes in The Session with 'reel' in their name",
        "sparql": """PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX ts:   <https://linkedmusic.ca/graphs/thesession/>
SELECT ?tune
WHERE {
  GRAPH ts: {
    ?tune a ts:Tune ;
          rdfs:label ?tuneLabel .
    FILTER (CONTAINS(LCASE(STR(?tuneLabel)), "reel"))
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all countries that have had more than 100 sessions in The Session.',
        "sparql": """PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX ts:   <https://linkedmusic.ca/graphs/thesession/>

SELECT ?country
WHERE {
  GRAPH ts: {
    ?session a ts:Session ;
             wdt:P17 ?country .
  }
}
GROUP BY ?country
HAVING (COUNT(?session) > 100)
LIMIT 10""",
    },
    {
        "nl": 'Determine the most prolific lyricist of each genre in the University of Tennessee Song Index. Do not count "traditional", "none", and "anonymous" as lyricists. List the genre and the corresponding lyricist. For ties, show each as a separate row.',
        "sparql": """PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX utsi: <https://linkedmusic.ca/graphs/utsi/>
SELECT ?genre ?lyricist
WHERE {
  GRAPH utsi: {
    
    # Subquery: count songs per lyricist per genre
    {
      SELECT ?genre ?lyricist (COUNT(DISTINCT ?song) AS ?songCount)
      WHERE {
        ?song a utsi:Song ;
              wdt:P676 ?lyricist ;
              wdt:P136 ?genre .
        FILTER(?lyricist != <http://www.wikidata.org/entity/Q4233718>)
        
        # New Filter: Exclude specific string literals (case-insensitive)
        FILTER(LCASE(STR(?lyricist)) NOT IN ("traditional", "none"))
      }
      GROUP BY ?genre ?lyricist 
    }
    
    # Subquery: pick top lyricist per genre
    {
      SELECT ?genre (MAX(?songCount) AS ?maxCount)
      WHERE {
        {
          SELECT ?genre ?lyricist (COUNT(DISTINCT ?song) AS ?songCount)
          WHERE {
            ?song a utsi:Song ;
                  wdt:P676 ?lyricist ;
                  wdt:P136 ?genre .
            FILTER(?lyricist != <http://www.wikidata.org/entity/Q4233718>)
            
            # New Filter: Must be mirrored here so the MAX count is accurate
            FILTER(LCASE(STR(?lyricist)) NOT IN ("traditional", "none"))
          }
          GROUP BY ?genre ?lyricist
        }
      }
      GROUP BY ?genre
    }
    # Match only lyricists that have the max count per genre
    FILTER(?songCount = ?maxCount)
  }
}
ORDER BY ?genre""",
    },
    {
        "nl": "Find all UTSI songs whose title contains the word 'love'",
        "sparql": """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX utsi: <https://linkedmusic.ca/graphs/utsi/>
SELECT ?song
WHERE {
  GRAPH utsi: {
    ?song a utsi:Song ;
          rdfs:label ?label .
    FILTER(CONTAINS(LCASE(STR(?label)), "love"))
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Return all genres in the University of Tennessee Song Index that have over 15000 songs.',
        "sparql": """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX utsi: <https://linkedmusic.ca/graphs/utsi/>

SELECT ?genre
WHERE {
  GRAPH utsi: {
    ?song a utsi:Song ;
          wdt:P136 ?genre .
  }
}
GROUP BY ?genre
HAVING (COUNT(?song) > 15000)""",
    },
    {
        "nl": 'Which performers in Weimar Jazz Database have performed at least two solos in the same key?',
        "sparql": """PREFIX wdt:    <http://www.wikidata.org/prop/direct/>
PREFIX wjazzd: <https://linkedmusic.ca/graphs/wjazzd/>
SELECT ?performer
WHERE {
  GRAPH wjazzd: {
    ?solo a wjazzd:Solo ;
          wdt:P175 ?performer ;
          wdt:P826 ?tonality .
  }
}
GROUP BY ?performer
HAVING (COUNT(DISTINCT ?solo) >= 2)
ORDER BY DESC(COUNT(DISTINCT ?solo))
LIMIT 100""",
    },
    {
        "nl": 'Which jazz compositions in the Weimar Jazz Database have more than 2 solos recorded?',
        "sparql": """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-replace#>
PREFIX wjazzd: <https://linkedmusic.ca/graphs/wjazzd/>

SELECT ?composition
WHERE {
  GRAPH wjazzd: {
    ?solo a wjazzd:Solo ;
          wdt:P2550 ?composition .
  }
}
GROUP BY ?composition
HAVING (COUNT(?solo) > 2)
LIMIT 100""",
    },
    {
        "nl": 'How many solos in the Weimar Jazz Database were recorded on each record label? Return the record label and the number of solos.',
        "sparql": """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wjazzd: <https://linkedmusic.ca/graphs/wjazzd/>
SELECT ?label (COUNT(?solo) AS ?soloCount)
WHERE {
  GRAPH wjazzd: {
    ?solo a wjazzd:Solo ;
          wdt:P361 ?track .
    ?track wdt:P361 ?record .
    ?record wdt:P264 ?label .
  }
}
GROUP BY ?label
ORDER BY DESC(?soloCount)
LIMIT 100""",
    },
    {
        "nl": 'Retrieve all events associated with G minor chants that are named after women from Cantus DB.',
        "sparql": """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd:  <http://www.wikidata.org/entity/>
PREFIX cdb: <https://linkedmusic.ca/graphs/cantusdb/>
SELECT ?event
WHERE {
  {
    SELECT DISTINCT ?event WHERE {
      GRAPH cdb: {
        ?chant wdt:P826 wd:Q283895 ;
               wdt:P837 ?event .
        FILTER(isURI(?event))
      }
    }
  }
  SERVICE <https://query.wikidata.org/sparql> {
    ?event wdt:P138 ?person .
    ?person wdt:P21 wd:Q6581072 .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'What are the 5 feast days with the most chants in Cantus DB, and what event or person are they named after according to Wikidata? Return the feast label in English and the named after label in English.',
        "sparql": """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX cdb: <https://linkedmusic.ca/graphs/cantusdb/>
SELECT ?feastLabel ?namedAfterLabel
WHERE {
  {
    SELECT ?feast (COUNT(?chant) AS ?chantCount) WHERE {
      GRAPH cdb: {
        ?chant wdt:P837 ?feast .
        FILTER(isURI(?feast))
      }
    }
    GROUP BY ?feast
    ORDER BY DESC(?chantCount)
    LIMIT 5
  }
  SERVICE <https://query.wikidata.org/sparql> {
    ?feast rdfs:label ?feastLabel .
    FILTER(LANG(?feastLabel) = "en")
    OPTIONAL {
      ?feast wdt:P138 ?namedAfter .
      ?namedAfter rdfs:label ?namedAfterLabel .
      FILTER(LANG(?namedAfterLabel) = "en")
    }
  }
}
ORDER BY DESC(?chantCount)""",
    },
    {
        "nl": 'What are the top 5 feast days with the most chants in Cantus Index?',
        "sparql": """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX cantusindex: <https://linkedmusic.ca/graphs/cantusindex/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT ?feast
WHERE {
  {
    SELECT ?feast (COUNT(?chant) AS ?chantCount) WHERE {
      GRAPH cantusindex: {
        ?chant wdt:P837 ?feast .
        FILTER(isURI(?feast))
      }
    }
    GROUP BY ?feast
    ORDER BY DESC(?chantCount)
    LIMIT 5
  }
}
ORDER BY DESC(?chantCount)""",
    },
    {
        "nl": "List all DIAMM compositions by Guillaume de Machaut and retrieve his birth year from Wikidata. Return two columns, one with the DIAMM composition IDs and the second with Guillaume de Machaut's birth year, populated for each composition.",
        "sparql": """PREFIX wd:    <http://www.wikidata.org/entity/>
PREFIX wdt:   <http://www.wikidata.org/prop/direct/>
PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>
PREFIX diamm: <https://linkedmusic.ca/graphs/diamm/>
SELECT ?composition ?birthDate
WHERE {
  {
    SELECT ?composition ?composerWikidata WHERE {
      GRAPH diamm: {
        ?composition a diamm:Composition ;
                     wdt:P86 ?composer .
        ?composer wdt:P2888 ?composerWikidata .
        FILTER(?composerWikidata = wd:Q200580)
      }
    }
  }
  SERVICE <https://query.wikidata.org/sparql> {
    ?composerWikidata wdt:P569 ?birthDate .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Return the inception dates of all DIAMM archives in France.',
        "sparql": """PREFIX wd:    <http://www.wikidata.org/entity/>
PREFIX wdt:   <http://www.wikidata.org/prop/direct/>
PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>
PREFIX diamm: <https://linkedmusic.ca/graphs/diamm/>
SELECT DISTINCT ?inceptionDate
WHERE {
  {
    SELECT ?archive ?archiveWikidata WHERE {
      GRAPH diamm: {
        ?archive a diamm:Archive ;
                 wdt:P2888 ?archiveWikidata ;
                 wdt:P131 ?city .
        ?city wdt:P17 ?country .
        ?country wdt:P2888 wd:Q142 .
      }
    }
  }
  SERVICE <https://query.wikidata.org/sparql> {
    OPTIONAL { ?archiveWikidata wdt:P571 ?inceptionDate . }
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Count how many solos were done by artists of each gender in Dig That Lick. Return one column for the gender and another for the number of solos.',
        "sparql": """PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX dtl:  <https://linkedmusic.ca/graphs/dig-that-lick/>
SELECT ?gender (SUM(?soloCount) AS ?totalSolos)
WHERE {
  {
    SELECT ?artist (COUNT(?solo) AS ?soloCount)
    WHERE {
      GRAPH dtl: {
        ?solo a dtl:Solo ;
              wdt:P175 ?artist .
              
        FILTER(isURI(?artist)) 
      }
    }
    GROUP BY ?artist
  }
  SERVICE <https://query.wikidata.org/sparql> {
    ?artist wdt:P21 ?gender . 
  }
}
GROUP BY ?gender""",
    },
    {
        "nl": 'Return the birth places of the 10 most prolific jazz soloists in Dig That Lick.',
        "sparql": """PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX dtl:  <https://linkedmusic.ca/graphs/dig-that-lick/>

SELECT DISTINCT ?birthCity
WHERE {
  {
    SELECT ?wdPerformer (COUNT(?solo) AS ?soloCount) WHERE {
      GRAPH dtl: {
        ?solo a dtl:Solo ;
              wdt:P361 ?track .
        ?track a dtl:Track ;
               wdt:P175 ?wdPerformer .
      }
    }
    GROUP BY ?wdPerformer
    ORDER BY DESC(?soloCount)
    LIMIT 10
  }
  SERVICE <https://query.wikidata.org/sparql> {
    ?wdPerformer wdt:P19 ?birthCity .
  }
}""",
    },
    {
        "nl": 'Find all MusicBrainz artists born in London. Return both their MusicBrainz ID and their Wikidata QID.',
        "sparql": """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX mb:   <https://linkedmusic.ca/graphs/musicbrainz/>

SELECT ?artist ?wdArtist
WHERE {
  SERVICE <https://query.wikidata.org/sparql> {
    ?wdArtist wdt:P19 wd:Q84 .
    ?wdArtist wdt:P106 wd:Q639669 .
  }
  GRAPH mb: {
    ?artist a mb:Artist ;
            wdt:P2888 ?wdArtist .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'What’s the average number of record labels that female singers in MusicBrainz have signed with?',
        "sparql": """PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX mb:   <https://linkedmusic.ca/graphs/musicbrainz/>
SELECT (AVG(?labelCount) AS ?averageLabelsPerSinger)
WHERE {
  {
    SELECT ?artist (COUNT(DISTINCT ?label) AS ?labelCount)
    WHERE {
      GRAPH mb: {
        ?artist a mb:Artist .
        ?artist wdt:P2888 ?artistWikidata .
        ?artist wdt:P264 ?label .
        ?artist wdt:P21 wd:Q6581072 .
      }
      SERVICE <https://query.wikidata.org/sparql> {
        ?artistWikidata wdt:P106 wd:Q177220 . 
      }
    }
    GROUP BY ?artist
  }
}""",
    },
    {
        "nl": 'For each institution in RISM that is also listed as an archive on Wikidata, what is the Wikidata QID of the country is it in?',
        "sparql": """PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX rism: <https://linkedmusic.ca/graphs/rism/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

SELECT ?instWD
WHERE {
  SERVICE <https://query.wikidata.org/sparql> {
    ?instWD wdt:P31  wd:Q166118 ;
            wdt:P17  ?countryWD .
    ?countryWD rdfs:label ?country .
    FILTER(LANG(?country) = "en")
  }
  GRAPH rism: {
    ?inst wdt:P2888 ?instWD ;
          rdfs:label ?label .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'What countries are the 10 most documented composers in RISM associated with according to Wikidata?',
        "sparql": """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX rism: <https://linkedmusic.ca/graphs/rism/>

SELECT DISTINCT ?country
WHERE {
  {
    SELECT ?composer ?composerQID (COUNT(?source) AS ?sourceCount) WHERE {
      GRAPH rism: {
        ?source wdt:P86 ?composer .
        ?composer wdt:P2888 ?composerQID .
      }
    }
    GROUP BY ?composer ?composerQID
    ORDER BY DESC(?sourceCount)
    LIMIT 10
  }
  SERVICE <https://query.wikidata.org/sparql> {
    ?composerQID wdt:P27 ?country .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all SIMSSA works whose composers appear as humans in Wikidata.',
        "sparql": """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX wd: <http://www.wikidata.org/entity/>
PREFIX simssa: <https://linkedmusic.ca/graphs/simssadb/>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
SELECT DISTINCT ?work
WHERE {
  {
    SELECT DISTINCT ?work ?composerQID WHERE {
      GRAPH simssa: {
        ?work a simssa:Work ;
              wdt:P86 ?composer .
        ?composer wdt:P2888 ?composerQID .
      }
    }
  }
  SERVICE <https://query.wikidata.org/sparql> {
    ?composerQID wdt:P31 wd:Q5 .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find works in the SIMSSA digital scores library whose composers were born in Italy.',
        "sparql": """PREFIX wdt:    <http://www.wikidata.org/prop/direct/>
PREFIX wd:     <http://www.wikidata.org/entity/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX simssa: <https://linkedmusic.ca/graphs/simssadb/>
SELECT DISTINCT ?work 
WHERE {
  {
    SELECT DISTINCT ?work ?composerQID WHERE {
      GRAPH simssa: {
        ?work a simssa:Work ;
              wdt:P86 ?composer .
        ?composer wdt:P2888 ?composerQID .
      }
    }
  }
  SERVICE <https://query.wikidata.org/sparql> {
    ?composerQID wdt:P19 ?birthplace .
    ?birthplace wdt:P17 wd:Q38 .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all Global Jukebox songs from countries in Asia',
        "sparql": """PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX gj:   <https://linkedmusic.ca/graphs/theglobaljukebox/>
SELECT DISTINCT ?song
WHERE {
  {
    SELECT ?song ?country
    WHERE {
      GRAPH gj: {
        ?song a gj:Song .
        ?song wdt:P2596 ?culture .
        ?culture wdt:P17 ?country .
      }
    }
  }
  SERVICE <https://query.wikidata.org/sparql> {
    ?country wdt:P30 wd:Q48 .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find the capital city of the country with the most sessions in The Session.',
        "sparql": """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX ts:   <https://linkedmusic.ca/graphs/thesession/>
SELECT ?capitalCity
WHERE {
  {
    SELECT ?country (COUNT(?session) AS ?sessionCount)
    WHERE {
      GRAPH ts: {
        ?session a ts:Session .
        ?session wdt:P17 ?country .
      }
    }
    GROUP BY ?country
    ORDER BY DESC(?sessionCount)
    LIMIT 1
  }
  SERVICE <https://query.wikidata.org/sparql> {
    ?country wdt:P36 ?capitalCity .
  }
}""",
    },
    {
        "nl": 'Find the ISO 3166-1 alpha-3 country code of all countries that have events in The Session.',
        "sparql": """PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX ts:   <https://linkedmusic.ca/graphs/thesession/>

SELECT DISTINCT ?isoCode
WHERE {
  {
    SELECT DISTINCT ?country
    WHERE {
      GRAPH ts: {
        ?event a ts:Events ;
               wdt:P17 ?country .
      }
    }
  }
  SERVICE <https://query.wikidata.org/sparql> {
    ?country wdt:P298 ?isoCode .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'What countries (return Wikidata QIDs) are the 5 most prolific composers (by number of songs) from in the University of Tennessee Song Index?',
        "sparql": """PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX utsi: <https://linkedmusic.ca/graphs/utsi/>

SELECT DISTINCT ?country
WHERE {
  {
    SELECT ?composer WHERE {
      GRAPH utsi: {
        ?song a utsi:Song ;
              wdt:P86 ?composer .
        FILTER(isURI(?composer))
      }
    }
    GROUP BY ?composer
    ORDER BY DESC(COUNT(?song))
    LIMIT 5
  }
  SERVICE <https://query.wikidata.org/sparql> {
    ?composer wdt:P27 ?country .
  }
}""",
    },
    {
        "nl": 'How many songs belong to each music genre in the University of Tennessee Song Index? Only return the number of songs.',
        "sparql": """PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX utsi: <https://linkedmusic.ca/graphs/utsi/>

SELECT ?songCount
WHERE {
  {
    SELECT ?genre (COUNT(DISTINCT ?song) AS ?songCount) WHERE {
      GRAPH utsi: {
        ?song a utsi:Song ;
              wdt:P136 ?genre .
        FILTER(isURI(?genre))
      }
    }
    GROUP BY ?genre
  }
}
ORDER BY DESC(?songCount)
LIMIT 100""",
    },
    {
        "nl": 'Find all solos in the Weimar Jazz Database whose performer was born in New Orleans.',
        "sparql": """PREFIX wd:     <http://www.wikidata.org/entity/>
PREFIX wdt:    <http://www.wikidata.org/prop/direct/>
PREFIX wjazzd: <https://linkedmusic.ca/graphs/wjazzd/>
SELECT DISTINCT ?solo
WHERE {
  SERVICE <https://query.wikidata.org/sparql> {
    ?performer wdt:P19 wd:Q34404 ;
               wdt:P106 wd:Q639669 .
  }
  GRAPH wjazzd: {
    ?solo a wjazzd:Solo ;
          wdt:P175 ?performer .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all jazz compositions in the Weimar Jazz Database written by musicians with Canadian citizenship, according to Wikidata.',
        "sparql": """PREFIX wdt:    <http://www.wikidata.org/prop/direct/>
PREFIX wd:     <http://www.wikidata.org/entity/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-format#>
PREFIX wjazzd: <https://linkedmusic.ca/graphs/wjazzd/>

SELECT DISTINCT ?composition
WHERE {
  {
    SELECT DISTINCT ?composition ?composerQID WHERE {
      GRAPH wjazzd: {
        ?composition a wjazzd:Composition ;
                     wdt:P86 ?composerQID .
        FILTER(isURI(?composerQID))
      }
    }
  }
  SERVICE <https://query.wikidata.org/sparql> {
    ?composerQID wdt:P27 wd:Q16 .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all compositions in DIAMM whose composer also appears as a composer in RISM',
        "sparql": """PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>
PREFIX wdt:   <http://www.wikidata.org/prop/direct/>
PREFIX diamm: <https://linkedmusic.ca/graphs/diamm/>
PREFIX rism:  <https://linkedmusic.ca/graphs/rism/>
SELECT DISTINCT ?composition
WHERE {
  GRAPH diamm: {
    ?composition a diamm:Composition ;
                 wdt:P86 ?composer .
    ?composer wdt:P2888 ?wikidata .
  }
  GRAPH rism: {
    ?rismComposer wdt:P2888 ?wikidata .
    ?rismSource wdt:P86 ?rismComposer .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all Dig That Lick tracks where the performer also has recordings in MusicBrainz',
        "sparql": """PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX dtl:  <https://linkedmusic.ca/graphs/dig-that-lick/>
PREFIX mb:   <https://linkedmusic.ca/graphs/musicbrainz/>
SELECT DISTINCT ?track 
WHERE {
  GRAPH dtl: {
    ?track a dtl:Track ;
           wdt:P175 ?wikidataArtist .
  }
  GRAPH mb: {
    ?mbArtist a mb:Artist ;
              wdt:P2888 ?wikidataArtist .
    ?recording a mb:Recording ;
               wdt:P175 ?mbArtist .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all entities in LinkedMusic with "death" in their label.',
        "sparql": """PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>

SELECT DISTINCT ?entity
WHERE {
  GRAPH ?graph {
    ?entity rdf:type  ?type ;
            rdfs:label ?label .
    FILTER (CONTAINS(LCASE(STR(?label)), "death"))
  }
  FILTER (
    STRSTARTS(STR(?graph), "https://linkedmusic.ca/graphs/")
  )
}
LIMIT 100""",
    },
    {
        "nl": 'Find all music events in The Session or MusicBrainz that happened on a day where at least one South Korean music label dissolved',
        "sparql": """PREFIX wd:  <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX mb:  <https://linkedmusic.ca/graphs/musicbrainz/>
PREFIX ts:  <https://linkedmusic.ca/graphs/thesession/>
SELECT DISTINCT ?event WHERE {
  GRAPH mb: {
    ?label a mb:Label ;
           wdt:P17 ?area ;
           wdt:P576 ?dissolutionDate .
    ?area wdt:P2888 wd:Q884 .
  }

  {
    GRAPH ts: {
      ?event a ts:Events ;
             wdt:P580 ?eventDate .
    }
  }
  UNION
  {
    GRAPH mb: {
      ?event a mb:Event ;
             wdt:P585 ?eventDate .
    }
  }

  FILTER (?eventDate = ?dissolutionDate)
}
LIMIT 100""",
    },
    {
        "nl": 'Find all musical instruments in the Global Jukebox featured in songs from Madagascar, and find recordings in MusicBrainz featuring these same instruments.',
        "sparql": """PREFIX wd:  <http://www.wikidata.org/entity/>
PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX gj:  <https://linkedmusic.ca/graphs/theglobaljukebox/>
PREFIX mb:  <https://linkedmusic.ca/graphs/musicbrainz/>
SELECT DISTINCT ?wikidataInstrument WHERE {
  GRAPH gj: {
    ?song wdt:P495 wd:Q1019 .
    ?song wdt:P870 ?wikidataInstrument .
  }
  GRAPH mb: {
    ?recording wdt:P870 ?musicBrainzInstrument .
    ?musicBrainzInstrument wdt:P2888 ?wikidataInstrument .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Return the Wikidata QID for institutions that appear in both DIAMM and RISM.',
        "sparql": """PREFIX rdfs: <http://www.w3.org/2000/01/rdf-format-ns#>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX diamm: <https://linkedmusic.ca/graphs/diamm/>
PREFIX rism:  <https://linkedmusic.ca/graphs/rism/>

SELECT DISTINCT ?wikidataLink
WHERE {
  GRAPH diamm: {
    ?diammArchive wdt:P2888 ?wikidataLink .
  }
  GRAPH rism: {
    ?rismInstitution wdt:P2888 ?wikidataLink .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Which feast day has the largest difference in chant counts between CantusDB and CantusIndex?',
        "sparql": """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX cdb: <https://linkedmusic.ca/graphs/cantusdb/>
PREFIX ci:  <https://linkedmusic.ca/graphs/cantusindex/>

SELECT ?feast (ABS(?cdbCount - ?ciCount) AS ?difference)
WHERE {
  {
    SELECT ?feast (COUNT(?chant) AS ?cdbCount)
    WHERE {
      GRAPH cdb: { ?chant wdt:P837 ?feast }
      FILTER(isLiteral(?feast))
    }
    GROUP BY ?feast
  }
  {
    SELECT ?feast (COUNT(?chant) AS ?ciCount)
    WHERE {
      GRAPH ci: { ?chant wdt:P837 ?feast }
      FILTER(isLiteral(?feast))
    }
    GROUP BY ?feast
  }
}
ORDER BY DESC(?difference)
LIMIT 1""",
    },
    {
        "nl": 'Find all cultures in the Global Jukebox from countries that have at least one RISM institution',
        "sparql": """PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX gj:   <https://linkedmusic.ca/graphs/theglobaljukebox/>
PREFIX rism:  <https://linkedmusic.ca/graphs/rism/>
SELECT DISTINCT ?culture
WHERE {
  GRAPH gj: {
    ?culture a gj:Culture ;
             wdt:P17 ?country .
  }
  GRAPH rism: {
    ?institution a rism:Institution ;
                 wdt:P2888 ?country .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all songs in The Global Jukebox from countries with more than four sessions in the Session.',
        "sparql": """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX gj:  <https://linkedmusic.ca/graphs/theglobaljukebox/>
PREFIX ts:  <https://linkedmusic.ca/graphs/thesession/>
SELECT DISTINCT ?song
WHERE {
  GRAPH gj: {
    ?song a gj:Song ;
          wdt:P495 ?country .
  }
  GRAPH ts: {
    SELECT ?country (COUNT(DISTINCT ?session) AS ?sessionCount)
    WHERE {
      ?session a ts:Session ;
               wdt:P17 ?country .
    }
    GROUP BY ?country
    HAVING (COUNT(DISTINCT ?session) > 4)
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all recordings in The Session whose performer also appears as an artist in MusicBrainz.',
        "sparql": """PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX ts:   <https://linkedmusic.ca/graphs/thesession/>
PREFIX mb:   <https://linkedmusic.ca/graphs/musicbrainz/>
SELECT DISTINCT ?recording
WHERE {
  GRAPH ts: {
    ?recording a ts:Recording ;
               wdt:P175 ?performerQID .
    FILTER(isURI(?performerQID))
  }
  GRAPH mb: {
    ?artist a mb:Artist ;
            wdt:P2888 ?performerQID .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all tracks in the Weimar Jazz Database whose performer also appears as an artist in MusicBrainz.',
        "sparql": """PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX wjazzd: <https://linkedmusic.ca/graphs/wjazzd/>
PREFIX mb:    <https://linkedmusic.ca/graphs/musicbrainz/>
SELECT DISTINCT ?track
WHERE {
  GRAPH wjazzd: {
    ?track a wjazzd:Track ;
           wdt:P175 ?performerQID .
  }
  GRAPH mb: {
    ?artist a mb:Artist ;
            wdt:P2888 ?performerQID .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find songs in the University of Tennessee Song Index whose composer also appears as an artist in MusicBrainz.',
        "sparql": """PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX utsi: <https://linkedmusic.ca/graphs/utsi/>
PREFIX mb:   <https://linkedmusic.ca/graphs/musicbrainz/>
SELECT DISTINCT ?song
WHERE {
  GRAPH utsi: {
    ?song a utsi:Song ;
          wdt:P86 ?composerQID .
    FILTER(isURI(?composerQID))
  }
  GRAPH mb: {
    ?artist a mb:Artist ;
            wdt:P2888 ?composerQID .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all works in SIMSSA DB whose composer also has compositions in DIAMM.',
        "sparql": """PREFIX wdt:    <http://www.wikidata.org/prop/direct/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
PREFIX simssa: <https://linkedmusic.ca/graphs/simssadb/>
PREFIX diamm:  <https://linkedmusic.ca/graphs/diamm/>
SELECT DISTINCT ?work
WHERE {
  GRAPH simssa: {
    ?work a simssa:Work ;
          wdt:P86 ?composer .
    ?composer wdt:P2888 ?composerQID .
  }
  GRAPH diamm: {
    ?diammPerson wdt:P2888 ?composerQID .
    ?diammComp   wdt:P86   ?diammPerson .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all feast names that appear in both Cantus DB and Cantus Index.',
        "sparql": """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX cdb: <https://linkedmusic.ca/graphs/cantusdb/>
PREFIX cantusindex: <https://linkedmusic.ca/graphs/cantusindex/>
SELECT DISTINCT ?feast
WHERE {
  GRAPH cdb: {
    ?chant wdt:P837 ?feast .
  }
  GRAPH cantusindex: {
    ?chant2 wdt:P837 ?feast .
  }
}
ORDER BY ?feast
LIMIT 100""",
    },
    {
        "nl": 'Find all tracks in Dig That Lick whose performer also has solos in the Weimar Jazz Database.',
        "sparql": """PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
PREFIX wdt:    <http://www.wikidata.org/prop/direct/>
PREFIX dtl:    <https://linkedmusic.ca/graphs/dig-that-lick/>
PREFIX wjazzd: <https://linkedmusic.ca/graphs/wjazzd/>
SELECT DISTINCT ?track
WHERE {
  GRAPH dtl: {
    ?track a dtl:Track ;
           wdt:P175 ?performerQID .
  }
  GRAPH wjazzd: {
    ?solo a wjazzd:Solo ;
          wdt:P175 ?performerQID .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all works in SIMSSA DB whose composer also has sources in RISM.',
        "sparql": """PREFIX wdt:    <http://www.wikidata.org/prop/direct/>
PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
PREFIX simssa: <https://linkedmusic.ca/graphs/simssadb/>
PREFIX rism:   <https://linkedmusic.ca/graphs/rism/>
SELECT DISTINCT ?work
WHERE {
  GRAPH simssa: {
    ?work a simssa:Work ;
          wdt:P86 ?simssaComposer .
    ?simssaComposer wdt:P2888 ?composerQID .
  }
  GRAPH rism: {
    ?rismPerson wdt:P2888 ?composerQID .
    ?rismSource wdt:P86 ?rismPerson .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all songs in the University of Tennessee Song Index whose composer also has compositions in DIAMM.',
        "sparql": """PREFIX wdt:   <http://www.wikidata.org/prop/direct/>
PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>
PREFIX utsi:  <https://linkedmusic.ca/graphs/utsi/>
PREFIX diamm: <https://linkedmusic.ca/graphs/diamm/>
SELECT DISTINCT ?song
WHERE {
  GRAPH utsi: {
    ?song a utsi:Song ;
          wdt:P86 ?composerQID .
    FILTER(isURI(?composerQID))
  }
  GRAPH diamm: {
    ?diammPerson wdt:P2888 ?composerQID .
    ?diammComp   wdt:P86   ?diammPerson .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all MusicBrainz recordings whose credited artist also has musical sources preserved in RISM.',
        "sparql": """PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX mb:   <https://linkedmusic.ca/graphs/musicbrainz/>
PREFIX rism: <https://linkedmusic.ca/graphs/rism/>
SELECT DISTINCT ?recording
WHERE {
  GRAPH mb: {
    ?recording a mb:Recording ;
               wdt:P175 ?artist .
    ?artist wdt:P2888 ?performerQID .
  }
  GRAPH rism: {
    ?rismPerson wdt:P2888 ?performerQID .
    ?rismSource wdt:P86 ?rismPerson .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all musical keys used in both Irish traditional music settings and jazz solos.',
        "sparql": """PREFIX wdt:    <http://www.wikidata.org/prop/direct/>
PREFIX ts:     <https://linkedmusic.ca/graphs/thesession/>
PREFIX wjazzd: <https://linkedmusic.ca/graphs/wjazzd/>
SELECT DISTINCT ?key
WHERE {
  GRAPH ts: {
    ?setting wdt:P826 ?key .
  }
  GRAPH wjazzd: {
    ?solo a wjazzd:Solo ;
          wdt:P826 ?key .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find composers whose works appear in DIAMM, RISM, and MusicBrainz.',
        "sparql": """PREFIX wdt:   <http://www.wikidata.org/prop/direct/>
PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>
PREFIX diamm: <https://linkedmusic.ca/graphs/diamm/>
PREFIX rism:  <https://linkedmusic.ca/graphs/rism/>
PREFIX mb:    <https://linkedmusic.ca/graphs/musicbrainz/>
SELECT DISTINCT ?composerQID
WHERE {
  GRAPH diamm: {
    ?diammPerson wdt:P2888 ?composerQID .
    ?diammComp wdt:P86 ?diammPerson .
  }
  GRAPH rism: {
    ?rismPerson wdt:P2888 ?composerQID .
    ?rismSource wdt:P86 ?rismPerson .
  }
  GRAPH mb: {
    ?mbRelease wdt:P86 ?mbArtist .
    ?mbArtist wdt:P2888 ?composerQID .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all archives in DIAMM that are also documented as institutions in RISM.',
        "sparql": """PREFIX wdt:   <http://www.wikidata.org/prop/direct/>
PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs:  <http://www.w3.org/2000/01/rdf-schema#>
PREFIX diamm: <https://linkedmusic.ca/graphs/diamm/>
PREFIX rism:  <https://linkedmusic.ca/graphs/rism/>
SELECT DISTINCT ?archive
WHERE {
  GRAPH diamm: {
    ?archive a diamm:Archive ;
             wdt:P2888 ?instQID .
  }
  GRAPH rism: {
    ?rismInst wdt:P2888 ?instQID .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all countries that have both folk music sessions in The Session and documented musical cultures in the Global Jukebox.',
        "sparql": """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX ts:  <https://linkedmusic.ca/graphs/thesession/>
PREFIX gj:  <https://linkedmusic.ca/graphs/theglobaljukebox/>
SELECT DISTINCT ?country
WHERE {
  GRAPH ts: {
    ?session wdt:P17 ?country .
  }
  GRAPH gj: {
    ?culture wdt:P17 ?country .
  }
}
ORDER BY ?country
LIMIT 100""",
    },
    {
        "nl": 'Find all instruments that appear in both solo recordings in Dig That Lick and songs in the Global Jukebox.',
        "sparql": """PREFIX wdt: <http://www.wikidata.org/prop/direct/>
PREFIX rdf: <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX dtl: <https://linkedmusic.ca/graphs/dig-that-lick/>
PREFIX gj:  <https://linkedmusic.ca/graphs/theglobaljukebox/>
SELECT DISTINCT ?instrument
WHERE {
  GRAPH dtl: {
    ?solo a dtl:Solo ;
          wdt:P870 ?instrument .
  }
  GRAPH gj: {
    ?song a gj:Song ;
          wdt:P870 ?instrument .
  }
}
ORDER BY ?instrument
LIMIT 100""",
    },
    {
        "nl": 'Find all songs in UTSI whose composer also has works catalogued in RISM.',
        "sparql": """PREFIX wdt:   <http://www.wikidata.org/prop/direct/>
PREFIX utsi:  <https://linkedmusic.ca/graphs/utsi/>
PREFIX rism:  <https://linkedmusic.ca/graphs/rism/>
SELECT DISTINCT ?song
WHERE {
  GRAPH utsi: {
    ?song a utsi:Song ;
          wdt:P86 ?composerQID .
    FILTER(isURI(?composerQID))
  }
  GRAPH rism: {
    ?rismPerson wdt:P2888 ?composerQID .
    ?rismSource wdt:P86 ?rismPerson .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all compositions in the Weimar Jazz Database whose composer also has works catalogued in RISM.',
        "sparql": """PREFIX wdt:    <http://www.wikidata.org/prop/direct/>
PREFIX wjazzd: <https://linkedmusic.ca/graphs/wjazzd/>
PREFIX rism:   <https://linkedmusic.ca/graphs/rism/>
SELECT DISTINCT ?comp
WHERE {
  GRAPH wjazzd: {
    ?comp a wjazzd:Composition ;
          wdt:P86 ?composerQID .
    FILTER(isURI(?composerQID))
  }
  GRAPH rism: {
    ?rismPerson wdt:P2888 ?composerQID .
    ?rismSource wdt:P86 ?rismPerson .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'What compositions in the Weimar Jazz Database share a title with a track in Dig That Lick?',
        "sparql": """PREFIX rdfs:   <http://www.w3.org/2000/01/rdf-schema#>
PREFIX wjazzd: <https://linkedmusic.ca/graphs/wjazzd/>
PREFIX dtl:    <https://linkedmusic.ca/graphs/dig-that-lick/>
SELECT DISTINCT ?comp
WHERE {
  GRAPH wjazzd: {
    ?comp a wjazzd:Composition ;
          rdfs:label ?title .
  }
  GRAPH dtl: {
    ?track a dtl:Track ;
           rdfs:label ?title .
  }
}
ORDER BY ?title
LIMIT 100""",
    },
    {
        "nl": 'Find composers whose works are encoded in SIMSSA and who are also catalogued as artists in MusicBrainz.',
        "sparql": """PREFIX wdt:    <http://www.wikidata.org/prop/direct/>
PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX simssa: <https://linkedmusic.ca/graphs/simssadb/>
PREFIX mb:     <https://linkedmusic.ca/graphs/musicbrainz/>
SELECT DISTINCT ?qid
WHERE {
  GRAPH simssa: {
    ?work rdf:type simssa:Work ;
          wdt:P86 ?composer .
    ?composer wdt:P2888 ?qid .
  }
  GRAPH mb: {
    ?artist wdt:P2888 ?qid .
  }
}
ORDER BY ?qid
LIMIT 100""",
    },
    {
        "nl": 'Find musical modes that appear in both Cantus DB chants and Weimar Jazz Database solos.',
        "sparql": """PREFIX wdt:    <http://www.wikidata.org/prop/direct/>
PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX cdb:    <https://linkedmusic.ca/graphs/cantusdb/>
PREFIX wjazzd: <https://linkedmusic.ca/graphs/wjazzd/>
SELECT DISTINCT ?mode
WHERE {
  GRAPH cdb: {
    ?chant wdt:P826 ?mode .
  }
  GRAPH wjazzd: {
    ?solo rdf:type wjazzd:Solo ;
          wdt:P826 ?mode .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all compositions in the Weimar Jazz Database whose composer also has songs documented in UTSI.',
        "sparql": """PREFIX wdt:    <http://www.wikidata.org/prop/direct/>
PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX utsi:   <https://linkedmusic.ca/graphs/utsi/>
PREFIX wjazzd: <https://linkedmusic.ca/graphs/wjazzd/>
SELECT DISTINCT ?comp
WHERE {
  GRAPH utsi: {
    ?song rdf:type utsi:Song ;
          wdt:P86 ?composerQID .
    FILTER(isURI(?composerQID))
  }
  GRAPH wjazzd: {
    ?comp rdf:type wjazzd:Composition ;
          wdt:P86 ?composerQID .
    FILTER(isURI(?composerQID))
  }
}
ORDER BY ?comp
LIMIT 100""",
    },
    {
        "nl": 'Find instruments that appear in solos in both Dig That Lick and the Weimar Jazz Database, and also feature in songs in the Global Jukebox.',
        "sparql": """PREFIX wdt:    <http://www.wikidata.org/prop/direct/>
PREFIX rdf:    <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX dtl:    <https://linkedmusic.ca/graphs/dig-that-lick/>
PREFIX wjazzd: <https://linkedmusic.ca/graphs/wjazzd/>
PREFIX gj:     <https://linkedmusic.ca/graphs/theglobaljukebox/>
SELECT DISTINCT ?instrument
WHERE {
  GRAPH dtl: {
    ?solo a dtl:Solo ;
          wdt:P870 ?instrument .
  }
  GRAPH wjazzd: {
    ?wSolo a wjazzd:Solo ;
           wdt:P870 ?instrument .
  }
  GRAPH gj: {
    ?song a gj:Song ;
          wdt:P870 ?instrument .
  }
}
ORDER BY ?instrument
LIMIT 100""",
    },
    {
        "nl": 'What countries have both traditional music sessions in The Session and popular songs documented in UTSI?',
        "sparql": """PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX ts:   <https://linkedmusic.ca/graphs/thesession/>
PREFIX utsi: <https://linkedmusic.ca/graphs/utsi/>
SELECT DISTINCT ?country
WHERE {
  GRAPH ts: {
    ?session a ts:Session ;
             wdt:P17 ?country .
    FILTER(isURI(?country))
  }
  GRAPH utsi: {
    ?song a utsi:Song ;
          wdt:P1071 ?country .
  }
}
ORDER BY ?country
LIMIT 100""",
    },
    {
        "nl": 'Find all works encoded in SIMSSA whose composer is also documented in both DIAMM and RISM.',
        "sparql": """PREFIX wdt:    <http://www.wikidata.org/prop/direct/>
PREFIX simssa: <https://linkedmusic.ca/graphs/simssadb/>
PREFIX rism:   <https://linkedmusic.ca/graphs/rism/>
PREFIX diamm:  <https://linkedmusic.ca/graphs/diamm/>
SELECT DISTINCT ?work
WHERE {
  GRAPH simssa: {
    ?work a simssa:Work ;
          wdt:P86 ?simssaComposer .
    ?simssaComposer wdt:P2888 ?composerQID .
  }
  GRAPH rism: {
    ?rismPerson wdt:P2888 ?composerQID .
    ?rismSource wdt:P86 ?rismPerson .
  }
  GRAPH diamm: {
    ?diammPerson wdt:P2888 ?composerQID .
    ?diammComp   wdt:P86   ?diammPerson .
  }
}
LIMIT 100""",
    },
    {
        "nl": 'Find all archives in DIAMM that also hold plainchant manuscript sources documented in Cantus DB.',
        "sparql": """PREFIX wdt:   <http://www.wikidata.org/prop/direct/>
PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX cdb:   <https://linkedmusic.ca/graphs/cantusdb/>
PREFIX diamm: <https://linkedmusic.ca/graphs/diamm/>
SELECT DISTINCT ?archive
WHERE {
  GRAPH cdb: {
    ?source a cdb:Source ;
            wdt:P276 ?locStr .
  }
  GRAPH diamm: {
    ?archive a diamm:Archive ;
             wdt:P11550 ?siglum .
  }
  FILTER(CONTAINS(STR(?locStr), CONCAT('(', STR(?siglum), ')')))
}
ORDER BY ?archive
LIMIT 100""",
    },
    {
        "nl": 'Find all countries that have medieval music manuscript archives in DIAMM and traditional music sessions in The Session.',
        "sparql": """PREFIX wdt:   <http://www.wikidata.org/prop/direct/>
PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX diamm: <https://linkedmusic.ca/graphs/diamm/>
PREFIX ts:    <https://linkedmusic.ca/graphs/thesession/>
SELECT DISTINCT ?countryQID
WHERE {
  GRAPH diamm: {
    ?archive a diamm:Archive ;
             wdt:P131 ?city .
    ?city wdt:P17 ?country .
    ?country wdt:P2888 ?countryQID .
  }
  GRAPH ts: {
    ?session a ts:Session ;
             wdt:P17 ?countryQID .
    FILTER(isURI(?countryQID))
  }
}
ORDER BY ?countryQID
LIMIT 100""",
    },
    {
        "nl": 'Find all tracks in Dig That Lick whose performer is also catalogued as a person in RISM.',
        "sparql": """PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX dtl:  <https://linkedmusic.ca/graphs/dig-that-lick/>
PREFIX rism: <https://linkedmusic.ca/graphs/rism/>
SELECT DISTINCT ?track
WHERE {
  GRAPH dtl: {
    ?solo a dtl:Solo ;
          wdt:P175 ?performerQID ;
          wdt:P361 ?track .
  }
  GRAPH rism: {
    ?rismPerson wdt:P2888 ?performerQID .
  }
}
ORDER BY ?track
LIMIT 100""",
    },
]
