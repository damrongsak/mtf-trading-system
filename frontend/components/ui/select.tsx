'use client';
import React, { createContext, useContext, useState, useEffect, useRef } from 'react';
import { ChevronDown } from 'lucide-react';
import { cn } from '@/lib/utils';

interface SelectContextType {
  value: string;
  onValueChange: (value: string) => void;
  open: boolean;
  setOpen: (open: boolean) => void;
  label: React.ReactNode;
  setLabel: (label: React.ReactNode) => void;
}

const SelectContext = createContext<SelectContextType | undefined>(undefined);

interface SelectProps {
  value: string;
  onValueChange: (value: string) => void;
  children: React.ReactNode;
}

export const Select: React.FC<SelectProps> = ({ value, onValueChange, children }) => {
  const [open, setOpen] = useState(false);
  const [label, setLabel] = useState<React.ReactNode>(null);

  // Close on outside click
  const ref = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (ref.current && !ref.current.contains(event.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, []);

  return (
    <SelectContext.Provider value={{ value, onValueChange, open, setOpen, label, setLabel }}>
      <div className="relative w-full text-left" ref={ref}>
        {children}
      </div>
    </SelectContext.Provider>
  );
};

interface SelectTriggerProps extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  children: React.ReactNode;
}

export const SelectTrigger: React.FC<SelectTriggerProps> = ({ className, children, ...props }) => {
  const context = useContext(SelectContext);
  if (!context) throw new Error("SelectTrigger must be used within a Select");
  const { open, setOpen } = context;

  return (
    <button
      type="button"
      className={cn(
        "flex h-10 w-full items-center justify-between rounded-md border border-gray-700 bg-gray-900/50 px-3 py-2 text-sm text-gray-100 ring-offset-background placeholder:text-gray-400 focus:outline-none focus:ring-1 focus:ring-blue-500 disabled:cursor-not-allowed disabled:opacity-50",
        className
      )}
      onClick={() => setOpen(!open)}
      {...props}
    >
      {children}
      <ChevronDown className="h-4 w-4 opacity-50" />
    </button>
  );
};

interface SelectValueProps {
  placeholder?: string;
  children?: React.ReactNode;
}

export const SelectValue: React.FC<SelectValueProps> = ({ placeholder, children }) => {
  const context = useContext(SelectContext);
  if (!context) throw new Error("SelectValue must be used within a Select");
  const { label } = context;
  
  return <span className="block truncate">{label || children || placeholder}</span>;
};

interface SelectContentProps extends React.HTMLAttributes<HTMLDivElement> {
  children: React.ReactNode;
}

export const SelectContent: React.FC<SelectContentProps> = ({ children, className, ...props }) => {
  const context = useContext(SelectContext);
  if (!context) throw new Error("SelectContent must be used within a Select");
  const { open } = context;

  // if (!open) return null; // Removed to allow SelectItems to register labels

  return (
    <div 
        className={cn(
            "absolute z-50 min-w-[8rem] overflow-hidden rounded-md border border-gray-700 bg-gray-900 text-gray-100 shadow-md animate-in fade-in-80 mt-1 w-full",
            !open && "hidden", 
            className
        )}
        {...props}
    >
      <div className="p-1">
        {children}
      </div>
    </div>
  );
};

interface SelectItemProps extends React.HTMLAttributes<HTMLDivElement> {
  value: string;
  children: React.ReactNode;
  disabled?: boolean;
}

export const SelectItem: React.FC<SelectItemProps> = ({ value, children, className, disabled, ...props }) => {
  const context = useContext(SelectContext);
  if (!context) throw new Error("SelectItem must be used within a Select");
  const { value: selectedValue, onValueChange, setOpen, setLabel } = context;

  const isSelected = value === selectedValue;

  useEffect(() => {
    if (isSelected) {
      setLabel(children);
    }
  }, [isSelected, children, setLabel]);

  return (
    <div
      aria-disabled={disabled}
      data-disabled={disabled}
      className={cn(
        "relative flex w-full cursor-pointer select-none items-center rounded-sm py-1.5 pl-2 pr-8 text-sm outline-none hover:bg-gray-800 focus:bg-gray-800 focus:text-accent-foreground",
        isSelected ? 'bg-gray-800 font-medium' : '',
        disabled && "pointer-events-none opacity-50",
        className
      )}
      onClick={() => {
        if (disabled) return;
        onValueChange(value);
        setOpen(false);
      }}
      {...props}
    >
      <span className="truncate">{children}</span>
    </div>
  );
};
