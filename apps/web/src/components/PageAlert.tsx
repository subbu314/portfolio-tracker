import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";

export function PageAlert({
  title = "Something went wrong",
  children,
}: {
  title?: string;
  children: React.ReactNode;
}) {
  return (
    <Alert variant="destructive" role="alert">
      <AlertTitle>{title}</AlertTitle>
      <AlertDescription>{children}</AlertDescription>
    </Alert>
  );
}
