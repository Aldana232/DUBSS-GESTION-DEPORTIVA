import { forwardRef, type InputHTMLAttributes, type ReactNode, type SelectHTMLAttributes, type TextareaHTMLAttributes } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/lib/utils";

const BASE =
  "w-full rounded-lg border border-ink-200 bg-white px-3 text-sm text-ink-900 placeholder:text-ink-400 " +
  "transition-colors hover:border-ink-300 focus-visible:border-brand-600 " +
  "disabled:cursor-not-allowed disabled:bg-ink-50 disabled:text-ink-500 " +
  "aria-[invalid=true]:border-brand-600 aria-[invalid=true]:bg-brand-50/40";

export const Input = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement> & { leading?: ReactNode; trailing?: ReactNode }>(
  function Input({ className, leading, trailing, ...props }, ref) {
    if (!leading && !trailing) return <input ref={ref} className={cn(BASE, "h-10", className)} {...props} />;
    return (
      <div className="relative">
        {leading && <span className="pointer-events-none absolute inset-y-0 left-3 flex items-center text-ink-400">{leading}</span>}
        <input ref={ref} className={cn(BASE, "h-10", leading && "pl-9", trailing && "pr-11", className)} {...props} />
        {trailing && <span className="absolute inset-y-0 right-1.5 flex items-center">{trailing}</span>}
      </div>
    );
  },
);

export const Select = forwardRef<HTMLSelectElement, SelectHTMLAttributes<HTMLSelectElement>>(
  function Select({ className, children, ...props }, ref) {
    return (
      <div className="relative">
        <select ref={ref} className={cn(BASE, "h-10 appearance-none pr-9", className)} {...props}>{children}</select>
        <ChevronDown aria-hidden="true" className="pointer-events-none absolute right-3 top-1/2 h-4 w-4 -translate-y-1/2 text-ink-400" />
      </div>
    );
  },
);

export const Textarea = forwardRef<HTMLTextAreaElement, TextareaHTMLAttributes<HTMLTextAreaElement>>(
  function Textarea({ className, rows = 3, ...props }, ref) {
    return <textarea ref={ref} rows={rows} className={cn(BASE, "resize-none py-2", className)} {...props} />;
  },
);

export const Checkbox = forwardRef<HTMLInputElement, InputHTMLAttributes<HTMLInputElement> & { label: string }>(
  function Checkbox({ label, className, id, ...props }, ref) {
    return (
      <label className={cn("inline-flex cursor-pointer items-center gap-2 text-sm text-ink-700", className)}>
        <input ref={ref} id={id} type="checkbox" className="h-4 w-4 rounded border-ink-300 accent-brand-600" {...props} />
        {label}
      </label>
    );
  },
);
