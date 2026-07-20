import { type ReactNode } from "react";

export function FormPanel({
  title,
  subtitle,
  tag,
  children,
}: {
  title: string;
  subtitle: string;
  tag: string;
  children: ReactNode;
}) {
  return (
    <div className="mx-auto flex h-[calc(100vh-3.5rem)] w-full max-w-4xl flex-col gap-6 overflow-y-auto px-6 py-8">
      <div>
        <span className="mono text-[10px] uppercase tracking-[0.3em] text-molten">
          {tag}
        </span>
        <h1 className="mt-2 font-display text-3xl font-semibold">{title}</h1>
        <p className="mt-1 text-sm text-muted-foreground">{subtitle}</p>
      </div>
      <div
        className="bracket-panel rounded-lg border border-hairline p-6"
        style={{ backgroundImage: "var(--gradient-panel)" }}
      >
        {children}
      </div>
    </div>
  );
}

export function FieldLabel({
  htmlFor,
  children,
  hint,
}: {
  htmlFor: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <label
      htmlFor={htmlFor}
      className="mono mb-1.5 flex items-center justify-between text-[10px] uppercase tracking-[0.25em] text-muted-foreground"
    >
      <span>{children}</span>
      {hint && <span className="text-molten/70">{hint}</span>}
    </label>
  );
}

export function TextField({
  id,
  value,
  onChange,
  placeholder,
  disabled,
}: {
  id: string;
  value: string;
  onChange: (v: string) => void;
  placeholder?: string;
  disabled?: boolean;
}) {
  return (
    <input
      id={id}
      value={value}
      onChange={(e) => onChange(e.target.value)}
      placeholder={placeholder}
      disabled={disabled}
      className="mono w-full rounded-md border border-hairline bg-background/60 px-3 py-2.5 text-sm text-foreground placeholder:text-muted-foreground/60 focus:border-molten focus:outline-none focus:ring-1 focus:ring-molten disabled:opacity-50"
    />
  );
}
