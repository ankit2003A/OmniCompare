import * as React from "react";
import { cn } from "@/lib/utils";

export function Input({ className, ...props }: React.InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn("h-10 w-full rounded-full border border-line bg-white px-4 text-sm placeholder:text-muted focus:border-ink", className)}
      {...props}
    />
  );
}
