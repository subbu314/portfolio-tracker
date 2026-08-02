import {
  Card,
  CardContent,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

export function DataTableCard({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <Card>
      <CardHeader className="p-5 pb-0">
        <CardTitle>{title}</CardTitle>
      </CardHeader>
      <CardContent className="p-5 pt-4">{children}</CardContent>
    </Card>
  );
}
