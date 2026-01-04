
import React from 'react';

interface SwitchProps extends Omit<React.ButtonHTMLAttributes<HTMLButtonElement>, 'onChange'> {
    checked: boolean;
    onCheckedChange: (checked: boolean) => void;
}

export const Switch: React.FC<SwitchProps> = ({ checked, onCheckedChange, className = '', disabled = false, ...props }) => {
    return (
        <button
            type="button"
            role="switch"
            aria-checked={checked}
            disabled={disabled}
            onClick={() => !disabled && onCheckedChange(!checked)}
            className={`
                relative inline-flex h-6 w-11 items-center rounded-full transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-slate-400 focus-visible:ring-offset-2 disabled:cursor-not-allowed disabled:opacity-50
                ${checked ? 'bg-emerald-600' : 'bg-slate-700'}
                ${className}
            `}
            {...props}
        >
            <span
                className={`
                    pointer-events-none block h-5 w-5 rounded-full bg-white shadow-lg ring-0 transition-transform
                    ${checked ? 'translate-x-5' : 'translate-x-0.5'}
                `}
            />
        </button>
    );
};
