import * as React from "react";
import { cva, type VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap rounded-full font-medium transition-colors disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "bg-ink text-white hover:bg-black",
        accent: "bg-accent text-white hover:bg-indigo-700",
        outline: "border border-line bg-white hover:bg-surface",
        ghost: "hover:bg-surface",
        link: "text-accent underline-offset-4 hover:underline",
      },
      size: { default: "h-10 px-5 text-sm", sm: "h-8 px-3 text-xs", lg: "h-12 px-7 text-base" },
    },
    defaultVariants: { variant: "default", size: "default" },
  }
);

export interface ButtonProps extends React.ButtonHTMLAttributes<HTMLButtonElement>, VariantProps<typeof buttonVariants> {}

export function Button({ className, variant, size, ...props }: ButtonProps) {
  return <button className={cn(buttonVariants({ variant, size }), className)} {...props} />;
}
export { buttonVariants };
