import { renderToStaticMarkup } from "react-dom/server";
import { describe, expect, it } from "vitest";
import { SearchNotes } from "@/components/SearchNotes";
import type { TranslateResult } from "@/hooks/useTranslate";
import { LanguageProvider } from "@/lib/i18n/context";

const query = "SELECT ?work WHERE {}";
const limitation = "Matching titles do not establish recording identity.";
const assessment: TranslateResult = {
  sparql: query,
  confidence: "medium",
  assumptions: ["Assumed QID Q123 for Example artist", limitation],
};

function renderNotes(result: TranslateResult | null, sparql = query) {
  return renderToStaticMarkup(
    <LanguageProvider>
      <SearchNotes assessment={result} sparql={sparql} />
    </LanguageProvider>,
  );
}

describe("SearchNotes", () => {
  it("shows limitations for the assessed query without exposing entity traces", () => {
    const html = renderNotes(assessment);
    expect(html).toContain("Search notes and limitations");
    expect(html).toContain(limitation);
    expect(html).not.toContain("Assumed QID");
    expect(assessment.assumptions).toHaveLength(2);
  });

  it("hides notes for an edited query and restores them for the assessed query", () => {
    expect(renderNotes(assessment, "SELECT ?person WHERE {}")).toBe("");
    expect(renderNotes(assessment)).toContain(limitation);
  });

  it("hides notes when a new search has cleared the assessment", () => {
    expect(renderNotes(null)).toBe("");
  });

  it.each([{ assumptions: [] }, { assumptions: ["Assumed QID Q123 for Example artist"] }])(
    "omits the panel when only internal traces or no notes are present: $assumptions",
    ({ assumptions }) => {
      expect(renderNotes({ ...assessment, assumptions })).toBe("");
    },
  );
});
