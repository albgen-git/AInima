import {
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
  TextareaHTMLAttributes,
  forwardRef,
  useId,
} from "react";
import { cn } from "@/lib/cn";

const fieldClasses =
  "w-full rounded-sm border border-border bg-ivory-light px-4 py-2.5 text-navy placeholder:text-slate/60 focus:border-navy focus:outline-none focus:ring-2 focus:ring-navy/15 disabled:bg-border disabled:text-slate";

interface FieldWrapperProps {
  label?: string;
  hint?: string;
  error?: string;
  required?: boolean;
  htmlFor: string;
  children: ReactNode;
}

function FieldWrapper({ label, hint, error, required, htmlFor, children }: FieldWrapperProps) {
  return (
    <div className="flex flex-col gap-1.5">
      {label && (
        <label htmlFor={htmlFor} className="text-sm font-medium text-navy">
          {label}
          {required && <span className="text-terracotta"> *</span>}
        </label>
      )}
      {children}
      {hint && !error && <p className="text-xs text-slate">{hint}</p>}
      {error && <p className="text-xs text-terracotta">{error}</p>}
    </div>
  );
}

interface TextFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  hint?: string;
  error?: string;
}

export const TextField = forwardRef<HTMLInputElement, TextFieldProps>(
  ({ label, hint, error, required, className, id, ...props }, ref) => {
    const autoId = useId();
    const fieldId = id ?? autoId;
    return (
      <FieldWrapper label={label} hint={hint} error={error} required={required} htmlFor={fieldId}>
        <input
          ref={ref}
          id={fieldId}
          className={cn(fieldClasses, error && "border-terracotta", className)}
          {...props}
        />
      </FieldWrapper>
    );
  }
);
TextField.displayName = "TextField";

interface SelectFieldProps extends SelectHTMLAttributes<HTMLSelectElement> {
  label?: string;
  hint?: string;
  error?: string;
}

export const SelectField = forwardRef<HTMLSelectElement, SelectFieldProps>(
  ({ label, hint, error, required, className, id, children, ...props }, ref) => {
    const autoId = useId();
    const fieldId = id ?? autoId;
    return (
      <FieldWrapper label={label} hint={hint} error={error} required={required} htmlFor={fieldId}>
        <select
          ref={ref}
          id={fieldId}
          className={cn(fieldClasses, error && "border-terracotta", className)}
          {...props}
        >
          {children}
        </select>
      </FieldWrapper>
    );
  }
);
SelectField.displayName = "SelectField";

interface TextareaFieldProps extends TextareaHTMLAttributes<HTMLTextAreaElement> {
  label?: string;
  hint?: string;
  error?: string;
}

export const TextareaField = forwardRef<HTMLTextAreaElement, TextareaFieldProps>(
  ({ label, hint, error, required, className, id, ...props }, ref) => {
    const autoId = useId();
    const fieldId = id ?? autoId;
    return (
      <FieldWrapper label={label} hint={hint} error={error} required={required} htmlFor={fieldId}>
        <textarea
          ref={ref}
          id={fieldId}
          className={cn(fieldClasses, "min-h-24 resize-y", error && "border-terracotta", className)}
          {...props}
        />
      </FieldWrapper>
    );
  }
);
TextareaField.displayName = "TextareaField";
