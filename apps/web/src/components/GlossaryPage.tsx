import { GlossaryTerm } from "@/components/GlossaryTerm";
import { GLOSSARY_TERMS } from "@/lib/glossary";

export function GlossaryPage() {
  return (
    <div className="stack">
      <header>
        <h1>Glossary</h1>
        <p className="muted">
          Plain-language definitions for portfolio values and return metrics.
        </p>
      </header>
      <nav className="glossary-jumps" aria-label="Jump to glossary term">
        {GLOSSARY_TERMS.map((term) => (
          <a key={term.id} href={`#${term.id}`}>
            {term.title}
          </a>
        ))}
      </nav>
      {GLOSSARY_TERMS.map((term) => (
        <GlossaryTerm key={term.id} term={term} />
      ))}
    </div>
  );
}
