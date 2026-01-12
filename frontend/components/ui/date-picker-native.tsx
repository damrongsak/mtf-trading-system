import * as React from "react";
import { format, parseISO } from "date-fns";
import { Calendar as CalendarIcon } from "lucide-react";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";

interface DatePickerNativeProps {
  value?: string;
  onChange: (value: string) => void;
  className?: string;
  placeholder?: string;
}

export function DatePickerNative({
  value,
  onChange,
  className,
  placeholder = "Pick a date",
}: DatePickerNativeProps) {
  const inputRef = React.useRef<HTMLInputElement>(null);

  const handleClick = () => {
    inputRef.current?.showPicker();
  };

  const displayValue = value ? (
    format(parseISO(value), "MMM d, yyyy HH:mm")
  ) : (
    <span className="text-slate-500">{placeholder}</span>
  );

  return (
    <div className={cn("relative", className)}>
      <Button
        variant="outline"
        className={cn(
          "w-full justify-start text-left font-normal bg-slate-950 border-slate-700 hover:bg-slate-900",
          !value && "text-muted-foreground"
        )}
        onClick={handleClick}
      >
        <CalendarIcon className="mr-2 h-4 w-4" />
        {displayValue}
      </Button>
      <input
        ref={inputRef}
        type="datetime-local"
        className="absolute inset-0 opacity-0 pointer-events-none"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        tabIndex={-1}
      />
    </div>
  );
}
