export const FEW_SHOT_EXAMPLES = [
  // ─── Challenge 1: Single-graph, Wikidata Q-ID lookup ───────────────────────

  {
    nl: "Find all compositions in DIAMM that are composed by Guillaume de Machaut",
    sparql: `PREFIX wd:    <http://www.wikidata.org/entity/>
PREFIX wdt:   <http://www.wikidata.org/prop/direct/>
PREFIX diamm: <https://linkedmusic.ca/graphs/diamm/>
SELECT ?composition
WHERE {
  GRAPH diamm: {
    ?composer wdt:P2888 wd:Q200580 .
    ?composition wdt:P86 ?composer .
  }
}`,
  },

  {
    nl: "Find all sessions in France in The Session",
    sparql: `PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX ts:   <https://linkedmusic.ca/graphs/thesession/>
SELECT ?session
WHERE {
  GRAPH ts: {
    ?session a ts:Session ;
             wdt:P17 wd:Q142 .
  }
}`,
  },

  {
    nl: "Find all MusicBrainz recordings made by Taylor Swift",
    sparql: `PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
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
}`,
  },

  {
    nl: "Find all Ethiopian songs in The Global Jukebox",
    sparql: `PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX gj:   <https://linkedmusic.ca/graphs/theglobaljukebox/>
SELECT ?song ?songLabel
WHERE {
  GRAPH gj: {
    ?song rdf:type gj:Song .
    ?song wdt:P495 wd:Q115 .
    OPTIONAL { ?song rdfs:label ?songLabel . }
  }
}`,
  },

  {
    nl: "Find all solos in Dig That Lick",
    sparql: `PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX dtl:  <https://linkedmusic.ca/graphs/dig-that-lick/>
SELECT ?solo
WHERE {
  GRAPH dtl: {
    ?solo rdf:type dtl:Solo .
  }
}`,
  },

  {
    nl: "Find all chants in Cantus DB in Lydian mode",
    sparql: `PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX cdb:  <https://linkedmusic.ca/graphs/cantusdb/>
SELECT ?chant
WHERE {
  GRAPH cdb: {
    ?chant wdt:P826 wd:Q686115 .
  }
}`,
  },

  {
    nl: "Find all sources in RISM held in the Bibliothèque nationale de France",
    sparql: `PREFIX wd:    <http://www.wikidata.org/entity/>
PREFIX wdt:   <http://www.wikidata.org/prop/direct/>
PREFIX rism:  <https://linkedmusic.ca/graphs/rism/>
SELECT ?source
WHERE {
  GRAPH rism: {
    ?source wdt:P276 ?institution .
    ?institution wdt:P2888 wd:Q193563 .
  }
}`,
  },

  // ─── Challenge 2: Aggregation, GROUP BY, DISTINCT ──────────────────────────

  {
    nl: "Find all DIAMM archives and sort them by the number of sources they contain",
    sparql: `PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
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
ORDER BY DESC(?sourceCount)`,
  },

  {
    nl: "Find all the different time signatures for jigs in The Session",
    sparql: `PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
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
ORDER BY ?timeSignature`,
  },

  {
    nl: "Find all bands that share at least two members with Radiohead in MusicBrainz",
    sparql: `PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
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
GROUP BY ?band
HAVING (COUNT(DISTINCT ?sharedMember) >= 2)
ORDER BY DESC(?sharedMemberCount)`,
  },

  {
    nl: "Find all Global Jukebox cultures that have at least one song with flute instrumentation",
    sparql: `PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX gj:   <https://linkedmusic.ca/graphs/theglobaljukebox/>
SELECT DISTINCT ?culture
WHERE {
  ?song a gj:Song .
  ?song wdt:P2596 ?culture .
  ?song wdt:P870 wd:Q11405 .
  ?culture a gj:Culture .
}`,
  },

  {
    nl: "Find all tracks in Dig That Lick recorded in New York City",
    sparql: `PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX dtl:  <https://linkedmusic.ca/graphs/dig-that-lick/>
SELECT DISTINCT ?track
WHERE {
  GRAPH dtl: {
    ?track a dtl:Track .
    ?track wdt:P8546 wd:Q60 .
  }
}`,
  },

  {
    nl: "Find compositions by Mendelssohn in RISM written in 9/8 time",
    sparql: `PREFIX wd:    <http://www.wikidata.org/entity/>
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
}`,
  },

  // ─── Challenge 3: Database + Wikidata federated queries ────────────────────

  {
    nl: "Find archives in DIAMM with an inception after 1900",
    sparql: `PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX wd:    <http://www.wikidata.org/entity/>
PREFIX wdt:   <http://www.wikidata.org/prop/direct/>
PREFIX diamm: <https://linkedmusic.ca/graphs/diamm/>
SELECT DISTINCT ?archive
WHERE {
  {
    SELECT ?archive ?archiveWikidata
    WHERE {
      GRAPH diamm: {
        ?archive a diamm:Archive ;
                 wdt:P2888 ?archiveWikidata .
      }
    }
  }
  SERVICE <https://query.wikidata.org/sparql> {
    ?archiveWikidata wdt:P571 ?inceptionDate .
    FILTER (YEAR(?inceptionDate) > 1900)
  }
}`,
  },

  {
    nl: "Find the capital city of the country with the most sessions in The Session",
    sparql: `PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
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
}`,
  },

  {
    nl: "What is the average number of record labels that female singers in MusicBrainz have signed with?",
    sparql: `PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX wd:   <http://www.wikidata.org/entity/>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX mb:   <https://linkedmusic.ca/graphs/musicbrainz/>
SELECT (AVG(?labelCount) AS ?averageLabelsPerSinger)
WHERE {
  {
    SELECT ?artist (COUNT(DISTINCT ?label) AS ?labelCount)
    WHERE {
      {
        SELECT ?artist ?artistWikidata ?label
        WHERE {
          GRAPH mb: {
            ?artist a mb:Artist .
            ?artist wdt:P2888 ?artistWikidata .
            ?artist wdt:P264 ?label .
            ?artist wdt:P21 wd:Q6581072 .
          }
        }
      }
      SERVICE <https://query.wikidata.org/sparql> {
        ?artistWikidata wdt:P106 wd:Q177220 .
      }
    }
    GROUP BY ?artist
  }
}`,
  },

  {
    nl: "Find all Global Jukebox songs from Africa",
    sparql: `PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
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
    ?country wdt:P30 wd:Q15 .
  }
}`,
  },

  {
    nl: "Count how many solos were done by artists of each gender in Dig That Lick",
    sparql: `PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
PREFIX wdt:  <http://www.wikidata.org/prop/direct/>
PREFIX dtl:  <https://linkedmusic.ca/graphs/dig-that-lick/>
SELECT ?gender (COUNT(?solo) AS ?soloCount)
WHERE {
  {
    SELECT ?solo ?artist
    WHERE {
      GRAPH dtl: {
        ?solo a dtl:Solo ;
              wdt:P175 ?artist .
      }
    }
  }
  SERVICE <https://query.wikidata.org/sparql> {
    ?artist wdt:P21 ?gender .
  }
}
GROUP BY ?gender`,
  },

  {
    nl: "Find composers in RISM who have siblings who are also composers in RISM",
    sparql: `PREFIX wdt:   <http://www.wikidata.org/prop/direct/>
PREFIX rism:  <https://linkedmusic.ca/graphs/rism/>
SELECT DISTINCT ?composer
WHERE {
  {
    SELECT ?composer ?wikicomposer
    WHERE {
      GRAPH rism: {
        ?work wdt:P86 ?composer .
        ?composer wdt:P2888 ?wikicomposer .
      }
    }
  }
  SERVICE <https://query.wikidata.org/sparql> {
    ?wikisibling wdt:P3373 ?wikicomposer .
  }
  GRAPH rism: {
    ?sibling wdt:P2888 ?wikisibling .
    ?work2 wdt:P86 ?sibling .
  }
}`,
  },

  // ─── Challenge 4: Cross-database integration ───────────────────────────────

  {
    nl: "Find all songs in The Global Jukebox from countries with more than four sessions in The Session",
    sparql: `PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
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
  {
    SELECT ?country (COUNT(DISTINCT ?session) AS ?sessionCount)
    WHERE {
      GRAPH ts: {
        ?session a ts:Session ;
                 wdt:P17 ?country .
      }
    }
    GROUP BY ?country
    HAVING (COUNT(DISTINCT ?session) > 4)
  }
}`,
  },

  {
    nl: "Find all works in MusicBrainz that, according to Dig That Lick, contain a solo performed by Charlie Parker",
    sparql: `PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
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
}`,
  },

  {
    nl: "Find all compositions or recordings with 'death' in the title across multiple databases",
    sparql: `PREFIX rdf:   <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
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
}`,
  },

  {
    nl: "Find all musical instruments in the Global Jukebox featured in songs indigenous to Madagascar, and find recordings in MusicBrainz featuring these same instruments",
    sparql: `PREFIX wd:   <http://www.wikidata.org/entity/>
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
}`,
  },

  {
    nl: "Find all music events that happened on a day where at least one South Korean music label dissolved",
    sparql: `PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
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
}`,
  },
];
