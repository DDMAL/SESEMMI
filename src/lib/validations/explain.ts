import { z } from "zod";

const languageSchema = z.enum(["en", "fr", "fa", "es", "de"]).default("en");

export const explainSchema = z.object({
  sparql: z.string().min(1, "SPARQL is required").max(5000),
  language: languageSchema,
});

export type ExplainInput = z.infer<typeof explainSchema>;

export const explainChatSchema = z.object({
  sparql: z.string().min(1, "SPARQL is required").max(5000),
  messages: z
    .array(
      z.object({
        role: z.enum(["user", "assistant"]),
        content: z.string().min(1).max(2000),
      }),
    )
    .max(40),
  language: languageSchema,
});

export type ExplainChatInput = z.infer<typeof explainChatSchema>;
