import React from 'react';
import Editor, { OnMount } from '@monaco-editor/react';
import { useAlphaStore } from '@/lib/stores/useAlphaStore';
import { useDebouncedCallback } from 'use-debounce';

const AlphaEditor = () => {
    const { formula, setFormula, runAlpha } = useAlphaStore();
    
    // Debounced preview
    const handlePreview = useDebouncedCallback(() => {
        runAlpha('preview');
    }, 500);

    const handleEditorChange = (value: string | undefined) => {
        if (value !== undefined) {
            setFormula(value);
            handlePreview();
        }
    };

    const handleEditorDidMount: OnMount = (editor, monaco) => {
        // Define Custom Theme
        monaco.editor.defineTheme('olympus-dark', {
            base: 'vs-dark',
            inherit: true,
            rules: [
                { token: 'keyword', foreground: 'C586C0' },
                { token: 'identifier', foreground: '9CDCFE' },
            ],
            colors: {
                'editor.background': '#0f172a00', // Transparent for glass effect
            }
        });
        monaco.editor.setTheme('olympus-dark');

        // Completion Provider
        monaco.languages.registerCompletionItemProvider('python', {
            // eslint-disable-next-line @typescript-eslint/no-explicit-any
            provideCompletionItems: (_model: any, _position: any) => {
                const suggestions = [
                    {
                        label: 'rank',
                        kind: monaco.languages.CompletionItemKind.Function,
                        insertText: 'rank(${1:series})',
                        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                        detail: 'Cross-sectional Rank'
                    },
                    {
                        label: 'delay',
                        kind: monaco.languages.CompletionItemKind.Function,
                        insertText: 'delay(${1:series}, ${2:period})',
                        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                        detail: 'Time-series lag'
                    },
                    {
                        label: 'close',
                        kind: monaco.languages.CompletionItemKind.Variable,
                        insertText: 'close',
                        detail: 'Close Price'
                    },
                    {
                        label: 'adx',
                        kind: monaco.languages.CompletionItemKind.Function,
                        insertText: 'adx(high, low, close, ${1:14})',
                        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                        detail: 'Trend Strength (ADX)'
                    },
                    {
                        label: 'di_plus',
                        kind: monaco.languages.CompletionItemKind.Function,
                        insertText: 'di_plus(high, low, close, ${1:14})',
                        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                        detail: 'Directional Indicator (+)'
                    },
                    {
                        label: 'di_minus',
                        kind: monaco.languages.CompletionItemKind.Function,
                        insertText: 'di_minus(high, low, close, ${1:14})',
                        insertTextRules: monaco.languages.CompletionItemInsertTextRule.InsertAsSnippet,
                        detail: 'Directional Indicator (-)'
                    }
                ];
                return { suggestions: suggestions };
            }
        });
    };

    return (
        <div className="h-full w-full border border-slate-800 rounded-lg overflow-hidden bg-slate-950/50 backdrop-blur-sm shadow-inner">
            <Editor
                height="100%"
                defaultLanguage="python"
                value={formula}
                onChange={handleEditorChange}
                onMount={handleEditorDidMount}
                options={{
                    minimap: { enabled: false },
                    fontSize: 14,
                    lineNumbers: 'on',
                    scrollBeyondLastLine: false,
                    automaticLayout: true,
                    padding: { top: 16, bottom: 16 },
                }}
            />
        </div>
    );
};

export default AlphaEditor;
