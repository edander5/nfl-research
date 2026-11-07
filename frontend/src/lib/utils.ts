// Only string class names are used by our small manually adapted shadcn primitives.
export const cn = (...classes: (string | undefined)[]) => classes.filter(Boolean).join(' ');
