import type { VariantProps } from "class-variance-authority"
import { cva } from "class-variance-authority"

export { default as Badge } from "./Badge.vue"

export const badgeVariants = cva(
  "inline-flex gap-1 items-center border-2 border-foreground px-3 py-1 text-xs font-bold uppercase tracking-wide shadow-brutal-sm",
  {
    variants: {
      variant: {
        default: "bg-primary text-foreground",
        secondary: "bg-surface text-foreground",
        destructive: "bg-destructive text-white",
        success: "bg-success text-white",
        warning: "bg-warning text-foreground",
        info: "bg-info text-white",
        outline: "bg-background text-foreground",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
)

export type BadgeVariants = VariantProps<typeof badgeVariants>
