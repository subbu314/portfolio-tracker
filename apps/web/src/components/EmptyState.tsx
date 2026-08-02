import Link from "next/link";
import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";

type Action = {
  label: string;
  href?: string;
  onClick?: () => void;
};

export function EmptyState({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: Action;
}) {
  return (
    <Card data-testid="empty-state">
      <CardHeader>
        <CardTitle>{title}</CardTitle>
        <CardDescription>{description}</CardDescription>
      </CardHeader>
      {action ? (
        <CardContent>
          {action.href ? (
            <Button asChild>
              <Link href={action.href}>{action.label}</Link>
            </Button>
          ) : (
            <Button type="button" onClick={action.onClick}>
              {action.label}
            </Button>
          )}
        </CardContent>
      ) : null}
    </Card>
  );
}
