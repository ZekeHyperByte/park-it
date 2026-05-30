import type { VariantProps } from "class-variance-authority"
import { cva } from "class-variance-authority"

export { default as Button } from "./Button.vue"

export const buttonVariants = cva(
  "inline-flex items-center justify-center gap-2 whitespace-nowrap border-2 border-foreground text-sm font-bold uppercase tracking-wide transition-all duration-100 focus-visible:outline-none disabled:pointer-events-none disabled:opacity-40 [&_svg]:pointer-events-none [&_svg]:size-4 [&_svg]:shrink-0",
  {
    variants: {
      variant: {
        default: "bg-primary text-foreground shadow-brutal hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none active:translate-x-[4px] active:translate-y-[4px]",
        destructive: "bg-destructive text-white shadow-brutal hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none active:translate-x-[4px] active:translate-y-[4px]",
        outline: "bg-background text-foreground shadow-brutal-sm hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none active:translate-x-[4px] active:translate-y-[4px]",
        secondary: "bg-surface text-foreground shadow-brutal-sm hover:translate-x-[2px] hover:translate-y-[2px] hover:shadow-none active:translate-x-[4px] active:translate-y-[4px]",
        ghost: "border-transparent shadow-none text-foreground hover:bg-surface hover:border-foreground hover:shadow-brutal-sm",
        link: "border-transparent shadow-none text-primary underline-offset-4 hover:underline",
      },
      size: {
        "default": "h-10 px-5 py-2",
        "sm": "h-8 px-3 text-xs",
        "lg": "h-12 px-7 text-lg",
        "icon": "h-10 w-10",
        "icon-sm": "size-9",
        "icon-lg": "size-11",
      },
    },
    defaultVariants: {
      variant: "default",
      size: "default",
    },
  },
)

export type ButtonVariants = VariantProps<typeof buttonVariants>
