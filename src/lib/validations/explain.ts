import { z } from "zod";

export const explainSchema = z.object({
  sparql: z.string().min(1, "SPARQL is required").max(5000),
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
});

export type ExplainChatInput = z.infer<typeof explainChatSchema>;
