import { unavailableClassName } from "@/lib/format";
import { cn } from "@/lib/utils";

type Props = {
  value: string;
  availableClassName: string;
  className?: string;
} & Omit<React.HTMLAttributes<HTMLParagraphElement>, "className" | "children">;

export function FormattedMetricValue({
  value,
  availableClassName,
  className,
  ...rest
}: Props) {
  return (
    <p
      className={cn(unavailableClassName(value, availableClassName), className)}
      {...rest}
    >
      {value}
    </p>
  );
}
