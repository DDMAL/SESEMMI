import {
  HighlightStyle,
  LanguageSupport,
  StreamLanguage,
  syntaxHighlighting,
} from "@codemirror/language";
import { tags } from "@lezer/highlight";

const KEYWORDS = new Set([
  "SELECT",
  "DISTINCT",
  "REDUCED",
  "FROM",
  "NAMED",
  "WHERE",
  "OPTIONAL",
  "FILTER",
  "UNION",
  "MINUS",
  "GRAPH",
  "SERVICE",
  "SILENT",
  "BIND",
  "VALUES",
  "GROUP",
  "BY",
  "HAVING",
  "ORDER",
  "ASC",
  "DESC",
  "LIMIT",
  "OFFSET",
  "PREFIX",
  "BASE",
  "CONSTRUCT",
  "DESCRIBE",
  "ASK",
  "INSERT",
  "DELETE",
  "DATA",
  "CLEAR",
  "DROP",
  "CREATE",
  "LOAD",
  "WITH",
  "USING",
  "INTO",
  "TRUE",
  "FALSE",
  "UNDEF",
  "IN",
  "NOT",
  "EXISTS",
  "AS",
  "COUNT",
  "SUM",
  "MIN",
  "MAX",
  "AVG",
  "SAMPLE",
  "COALESCE",
  "IF",
  "ISIRI",
  "ISURI",
  "ISBLANK",
  "ISLITERAL",
  "ISNUMERIC",
  "REGEX",
  "BOUND",
  "STR",
  "LANG",
  "DATATYPE",
  "LANGMATCHES",
  "STRSTARTS",
  "STRENDS",
  "CONTAINS",
  "STRLEN",
  "SUBSTR",
  "UCASE",
  "LCASE",
  "CONCAT",
  "REPLACE",
  "UUID",
  "STRUUID",
  "NOW",
  "YEAR",
  "MONTH",
  "DAY",
  "HOURS",
  "MINUTES",
  "SECONDS",
  "TIMEZONE",
  "TZ",
  "MD5",
  "SHA1",
  "SHA256",
  "SHA384",
  "SHA512",
  "ABS",
  "CEIL",
  "FLOOR",
  "ROUND",
  "RAND",
  "ENCODE_FOR_URI",
  "STRLANG",
  "STRDT",
  "SAMETERM",
  "IRI",
  "URI",
  "BNODE",
  "GROUP_CONCAT",
  "SEPARATOR",
]);

function eatString(stream: { next: () => string | void }, quote: string) {
  let escaped = false;
  let ch: string | void;
  while ((ch = stream.next()) != null) {
    if (ch === quote && !escaped) break;
    escaped = !escaped && ch === "\\";
  }
}

const sparqlStreamLang = StreamLanguage.define<object>({
  token(stream) {
    if (stream.eatSpace()) return null;

    // comment
    if (stream.eat("#")) {
      stream.skipToEnd();
      return "comment";
    }

    // triple-quoted strings (must check before single-quote)
    if (stream.match('"""')) {
      while (!stream.match('"""')) {
        if (stream.next() == null) break;
      }
      return "string";
    }
    if (stream.match("'''")) {
      while (!stream.match("'''")) {
        if (stream.next() == null) break;
      }
      return "string";
    }

    // single-quoted strings
    if (stream.eat('"')) {
      eatString(stream, '"');
      return "string";
    }
    if (stream.eat("'")) {
      eatString(stream, "'");
      return "string";
    }

    // URIs
    if (stream.eat("<")) {
      stream.skipTo(">");
      stream.eat(">");
      return "link";
    }

    // variables
    if (stream.eat("?") || stream.eat("$")) {
      stream.eatWhile(/\w/);
      return "variableName";
    }

    // numbers
    if (stream.match(/^-?\d+(\.\d+)?([eE][+-]?\d+)?/)) {
      return "number";
    }

    // keywords and prefixed names
    if (stream.match(/^[a-zA-Z_]\w*/)) {
      const word = stream.current().toUpperCase();
      if (KEYWORDS.has(word)) return "keyword";
      // prefixed name: prefix:local
      if (stream.eat(":")) {
        stream.eatWhile(/[\w.-]/);
        return "typeName";
      }
      return null;
    }

    // standalone colon (e.g. the colon in a bare prefix declaration)
    if (stream.eat(":")) {
      stream.eatWhile(/[\w.-]/);
      return "typeName";
    }

    stream.next();
    return null;
  },
});

export const sparqlHighlightStyle = HighlightStyle.define([
  { tag: tags.keyword, color: "#4f46e5", fontWeight: "600" },
  { tag: tags.variableName, color: "#b45309" },
  { tag: tags.url, color: "#059669" },
  { tag: tags.typeName, color: "#0891b2" },
  { tag: tags.string, color: "#be185d" },
  { tag: tags.number, color: "#1d4ed8" },
  { tag: tags.comment, color: "#94a3b8", fontStyle: "italic" },
]);

export const sparqlSyntaxHighlighting = syntaxHighlighting(sparqlHighlightStyle);

export function sparqlLanguageSupport(): LanguageSupport {
  return new LanguageSupport(sparqlStreamLang);
}
