import { GlossaryTerm } from "@/components/GlossaryTerm";
import { Button } from "@/components/ui/button";
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
      <nav
        className="flex flex-wrap gap-2"
        aria-label="Jump to glossary term"
      >
        {GLOSSARY_TERMS.map((term) => (
          <Button key={term.id} asChild variant="outline" size="sm">
            <a href={`#${term.id}`}>{term.title}</a>
          </Button>
        ))}
      </nav>
      {GLOSSARY_TERMS.map((term) => (
        <GlossaryTerm key={term.id} term={term} />
      ))}
    </div>
  );
}
