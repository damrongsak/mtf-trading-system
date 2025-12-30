'use client';

import React, { useState, KeyboardEvent } from 'react';
import { X } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';

interface TagsInputProps {
    value?: string[];
    onChange: (tags: string[]) => void;
    placeholder?: string;
    className?: string;
}

export function TagsInput({ value = [], onChange, placeholder, className }: TagsInputProps) {
    const [inputValue, setInputValue] = useState('');

    const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter' || e.key === ',') {
            e.preventDefault();
            addTag();
        } else if (e.key === 'Backspace' && !inputValue && value.length > 0) {
            removeTag(value.length - 1);
        }
    };

    const addTag = () => {
        const trimmed = inputValue.trim();
        if (trimmed && !value.includes(trimmed)) {
            onChange([...value, trimmed]);
            setInputValue('');
        }
    };

    const removeTag = (index: number) => {
        const newTags = [...value];
        newTags.splice(index, 1);
        onChange(newTags);
    };

    return (
        <div className={cn("flex flex-wrap gap-2 p-2 border border-input rounded-md bg-transparent", className)}>
            {value.map((tag, index) => (
                <Badge key={`${tag}-${index}`} variant="secondary" className="flex items-center gap-1">
                    {tag}
                    <button
                        type="button"
                        onClick={() => removeTag(index)}
                        className="text-muted-foreground hover:text-foreground"
                    >
                        <X className="h-3 w-3" />
                        <span className="sr-only">Remove {tag}</span>
                    </button>
                </Badge>
            ))}
            <Input
                type="text"
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                onBlur={addTag}
                placeholder={value.length === 0 ? placeholder : ''}
                className="flex-1 min-w-[120px] border-none shadow-none focus-visible:ring-0 p-0 h-auto bg-transparent"
            />
        </div>
    );
}
