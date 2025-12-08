import React from 'react';

interface CardProps {
  children: React.ReactNode;
  className?: string;
}

export const Card: React.FC<CardProps> = ({ children, className = '' }) => {
  return (
    <div className={`rounded-xl border border-gray-800 bg-gray-950/50 backdrop-blur-md ${className}`}>
      {children}
    </div>
  );
};
