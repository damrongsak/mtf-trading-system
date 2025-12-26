
import React from 'react';

interface AlertProps {
    children: React.ReactNode;
    className?: string;
    variant?: 'default' | 'destructive';
}

export const Alert: React.FC<AlertProps> = ({ children, className = '', variant: _variant = 'default' }) => {
    return (
        <div role="alert" className={`relative w-full rounded-lg border p-4 [&>svg]:absolute [&>svg]:left-4 [&>svg]:top-4 [&>svg+div]:translate-y-[-3px] [&:has(svg)]:pl-11 ${className}`}>
            {children}
        </div>
    );
};

export const AlertTitle: React.FC<{ children: React.ReactNode, className?: string }> = ({ children, className = '' }) => (
    <h5 className={`mb-1 font-medium leading-none tracking-tight ${className}`}>{children}</h5>
);

export const AlertDescription: React.FC<{ children: React.ReactNode, className?: string }> = ({ children, className = '' }) => (
    <div className={`text-sm [&_p]:leading-relaxed ${className}`}>{children}</div>
);
