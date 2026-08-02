import type { GlossaryTermDefinition } from "@/lib/glossary";
import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

type GlossaryTermProps = {
  term: GlossaryTermDefinition;
};

export function GlossaryTerm({ term }: GlossaryTermProps) {
  return (
    <Card id={term.id} className="scroll-mt-4">
      <CardHeader className="p-5 pb-0">
        <CardTitle>{term.title}</CardTitle>
      </CardHeader>
      <CardContent className="p-5 pt-4">
        <p>{term.body}</p>
      </CardContent>
    </Card>
  );
}
