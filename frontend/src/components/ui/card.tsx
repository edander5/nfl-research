// Adapted from shadcn/ui Card (MIT); notice in frontend/THIRD_PARTY_NOTICES.md.
import type { ComponentProps } from 'react';
import { cn } from '../../lib/utils';
export function Card({ className = '', ...props }: ComponentProps<'div'>) {
  return <div data-slot="card" className={cn("flex flex-col rounded-xl border bg-card text-card-foreground shadow-sm", className)} {...props} />;
}
export function CardContent({ className = '', ...props }: ComponentProps<'div'>) {
  return <div data-slot="card-content" className={cn("p-6", className)} {...props} />;
}
