import type { GlossaryTermDefinition } from "@/lib/glossary";

type GlossaryTermProps = {
  term: GlossaryTermDefinition;
};

export function GlossaryTerm({ term }: GlossaryTermProps) {
  return (
    <section className="panel" id={term.id}>
      <h2>{term.title}</h2>
      <p>{term.body}</p>
    </section>
  );
}
