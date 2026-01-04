'use client';

import React, { useState, KeyboardEvent, useRef } from 'react';
import { X, Trash2 } from 'lucide-react';
import { Input } from '@/components/ui/input';
import { cn } from '@/lib/utils';
import { Badge } from '@/components/ui/badge';
import { Button } from '@/components/ui/button';

interface TagsInputProps {
    value?: string[];
    onChange: (tags: string[]) => void;
    placeholder?: string;
    className?: string;
}

export function TagsInput({ value = [], onChange, placeholder, className }: TagsInputProps) {
    const [inputValue, setInputValue] = useState('');
    const [selectedIndices, setSelectedIndices] = useState<Set<number>>(new Set());
    const [lastSelectedIndex, setLastSelectedIndex] = useState<number | null>(null);
    const containerRef = useRef<HTMLDivElement>(null);

    const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
        if (e.key === 'Enter' || e.key === ',') {
            e.preventDefault();
            addTag();
        } else if ((e.key === 'Backspace' || e.key === 'Delete')) {
            if (!inputValue) {
                if (selectedIndices.size > 0) {
                    deleteSelectedTags();
                } else if (value.length > 0) {
                    // Default behavior: delete last tag if nothing selected
                    removeTag(value.length - 1);
                }
            }
        }
    };

    // Handle global keydown for delete when not focused on input but tags are selected
    const handleContainerKeyDown = (e: React.KeyboardEvent) => {
         if ((e.key === 'Backspace' || e.key === 'Delete') && selectedIndices.size > 0 && !inputValue) {
            e.preventDefault();
            deleteSelectedTags();
        }
    };

    const addTag = () => {
        const trimmed = inputValue.trim();
        if (trimmed && !value.includes(trimmed)) {
            onChange([...value, trimmed]);
            setInputValue('');
            setSelectedIndices(new Set()); // Clear selection on add
        }
    };

    const removeTag = (index: number) => {
        const newTags = [...value];
        newTags.splice(index, 1);
        onChange(newTags);
        
        // Update selection indices
        const newSelection = new Set<number>();
        selectedIndices.forEach(i => {
            if (i < index) newSelection.add(i);
            if (i > index) newSelection.add(i - 1);
        });
        setSelectedIndices(newSelection);
    };

    const deleteSelectedTags = () => {
        const newTags = value.filter((_, index) => !selectedIndices.has(index));
        onChange(newTags);
        setSelectedIndices(new Set());
        setLastSelectedIndex(null);
    };

    const handleTagClick = (index: number, e: React.MouseEvent) => {
        e.stopPropagation(); // Prevent container focus logic if needed
        
        const newSelection = new Set(e.ctrlKey || e.metaKey ? selectedIndices : []);

        if (e.shiftKey && lastSelectedIndex !== null) {
            const start = Math.min(lastSelectedIndex, index);
            const end = Math.max(lastSelectedIndex, index);
            for (let i = start; i <= end; i++) {
                newSelection.add(i);
            }
        } else {
            if (e.ctrlKey || e.metaKey) {
                 if (newSelection.has(index)) {
                    newSelection.delete(index);
                } else {
                    newSelection.add(index);
                }
            } else {
                // Regular click: select only this one (toggle if already selected?) 
                // typically regular click selects just this one. 
                // To allow easy "deselect all by clicking background", we handle that on container?
                // For now, let's make simple click toggle if it's the only one, or select just it.
                 if (selectedIndices.size === 1 && selectedIndices.has(index)) {
                    newSelection.clear();
                 } else {
                     newSelection.clear();
                     newSelection.add(index);
                 }
            }
        }

        setSelectedIndices(newSelection);
        setLastSelectedIndex(index);
    };

    return (
        <div 
            ref={containerRef}
            className={cn("flex flex-col gap-2 p-2 border border-input rounded-md bg-transparent", className)}
            onKeyDown={handleContainerKeyDown}
            tabIndex={-1} // Allow receiving key events if focused programmatically or clicked
        >
            <div className="flex justify-between items-center mb-1">
                <span className="text-xs text-muted-foreground">
                    {value.length} items • {selectedIndices.size > 0 ? `${selectedIndices.size} selected` : 'Click to select'}
                </span>
                {selectedIndices.size > 0 && (
                    <Button 
                        variant="ghost" 
                        size="sm" 
                        onClick={deleteSelectedTags}
                        className="h-6 px-2 text-destructive hover:text-destructive hover:bg-destructive/10"
                    >
                        <Trash2 className="h-3 w-3 mr-1" /> Remove Selected
                    </Button>
                )}
            </div>
            
            <div className="flex flex-wrap gap-2">
                {value.map((tag, index) => {
                    const isSelected = selectedIndices.has(index);
                    return (
                        <Badge 
                            key={`${tag}-${index}`} 
                            variant={isSelected ? "default" : "secondary"} 
                            className={cn(
                                "flex items-center gap-1 cursor-pointer select-none transition-colors",
                                isSelected ? "bg-primary text-primary-foreground hover:bg-primary/90 ring-2 ring-offset-1 ring-primary" : "hover:bg-secondary/80"
                            )}
                            onClick={(e) => handleTagClick(index, e)}
                        >
                            {tag}
                            <button
                                type="button"
                                onClick={(e) => {
                                    e.stopPropagation();
                                    removeTag(index);
                                }}
                                className="text-muted-foreground hover:text-foreground ml-1"
                            >
                                <X className="h-3 w-3" />
                                <span className="sr-only">Remove {tag}</span>
                            </button>
                        </Badge>
                    );
                })}
                <Input
                    type="text"
                    value={inputValue}
                    onChange={(e) => setInputValue(e.target.value)}
                    onKeyDown={handleKeyDown}
                    onBlur={() => {
                        // Optional: clear selection on blur? No, might want to keep selection.
                        addTag();
                    }}
                    onFocus={() => {
                       // potentially clear selection when typing starts?
                    }}
                    placeholder={value.length === 0 ? placeholder : ''}
                    className="flex-1 min-w-[120px] border-none shadow-none focus-visible:ring-0 p-0 h-auto bg-transparent"
                />
            </div>
        </div>
    );
}
