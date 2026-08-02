import { render, screen } from "@testing-library/react";
import { Alert, AlertDescription, AlertTitle } from "@/components/ui/alert";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";

it("renders Button, Alert, and Skeleton", () => {
  render(
    <>
      <Button>Refresh holdings</Button>
      <Alert>
        <AlertTitle>Holdings may be outdated</AlertTitle>
        <AlertDescription>Sync to update prices.</AlertDescription>
      </Alert>
      <Skeleton data-testid="skel" className="h-8 w-32" />
    </>,
  );

  expect(
    screen.getByRole("button", { name: /refresh holdings/i }),
  ).toBeInTheDocument();
  expect(screen.getByText(/holdings may be outdated/i)).toBeInTheDocument();
  expect(screen.getByTestId("skel")).toBeInTheDocument();
});
