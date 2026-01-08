"use client";

import React, { useState, useEffect } from 'react';
import Editor from '@monaco-editor/react';
import { defaultApi } from '@/lib/api/client';
import { SystemPromptResponse } from '@/lib/api/generated';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '@/components/ui/card';
import { Badge } from '@/components/ui/badge';
import { toast } from 'sonner';
import { Plus, Save, Play, Edit2, Code } from 'lucide-react';

export function PromptEditor() {
    const [prompts, setPrompts] = useState<SystemPromptResponse[]>([]);
    const [selectedPrompt, setSelectedPrompt] = useState<SystemPromptResponse | null>(null);
    const [isEditing, setIsEditing] = useState(false);
    const [isLoading, setIsLoading] = useState(false);
    
    // Edit Form State
    const [editName, setEditName] = useState("");
    const [editDesc, setEditDesc] = useState("");
    const [editTemplate, setEditTemplate] = useState("");
    const [editVars, setEditVars] = useState<string[]>([]);
    
    // Render Test State
    const [testVars, setTestVars] = useState("{}");
    const [renderResult, setRenderResult] = useState("");

    const fetchPrompts = async () => {
        setIsLoading(true);
        try {
            const response = await defaultApi.apiV1PromptsGet();
            if (response.data.data) {
                setPrompts(response.data.data);
            }
        } catch (error) {
            toast.error("Failed to load prompts");
            console.error(error);
        } finally {
            setIsLoading(false);
        }
    };

    useEffect(() => {
        fetchPrompts();
    }, []);

    const handleSelect = (prompt: SystemPromptResponse) => {
        setSelectedPrompt(prompt);
        setEditName(prompt.name || "");
        setEditDesc(prompt.description || "");
        setEditTemplate(prompt.template || "");
        setEditVars(prompt.input_variables || []);
        setIsEditing(false);
        setRenderResult("");
    };

    const handleCreateNew = () => {
        setSelectedPrompt(null);
        setEditName("New Prompt");
        setEditDesc("");
        setEditTemplate("You are a helpful assistant.");
        setEditVars([]);
        setIsEditing(true);
    };

    const handleSave = async () => {
        try {
            // Auto-parse variables from template
            const regex = /{{\s*(\w+)\s*}}/g;
            const matches = [...editTemplate.matchAll(regex)];
            const variables = Array.from(new Set(matches.map(m => m[1])));

            if (selectedPrompt && selectedPrompt.id) {
                // Update
                const response = await defaultApi.apiV1PromptsIdPut({
                    id: selectedPrompt.id,
                    systemPromptUpdate: {
                        description: editDesc,
                        template: editTemplate,
                        input_variables: variables
                    }
                });
                toast.success("Prompt updated");
                if (response.data.data) {
                    handleSelect(response.data.data);
                }
            } else {
                // Create
                const response = await defaultApi.apiV1PromptsPost({
                    systemPromptCreate: {
                        name: editName,
                        template: editTemplate,
                        description: editDesc,
                        input_variables: variables,
                        is_active: true
                    }
                });
                toast.success("Prompt created");
                if (response.data.data) {
                    handleSelect(response.data.data);
                }
            }
            fetchPrompts();
            setIsEditing(false);
        } catch (error: any) {
             const msg = error.response?.data?.message || error.message || "Failed to save";
             toast.error(msg);
        }
    };

    const handleRenderTest = async () => {
        if (!selectedPrompt || !selectedPrompt.id) return;
        try {
            const vars = JSON.parse(testVars);
            const response = await defaultApi.apiV1PromptsIdRenderPost({
                id: selectedPrompt.id,
                apiV1PromptsIdRenderPostRequest: vars
            });
            if (response.data.data) {
                setRenderResult(response.data.data.rendered_text || "");
                if (response.data.data.missing_variables && response.data.data.missing_variables.length > 0) {
                    toast.warning(`Missing variables: ${response.data.data.missing_variables.join(", ")}`);
                }
            }
        } catch (e) {
            toast.error("Invalid JSON or Render Error");
        }
    };

    return (
        <div className="grid grid-cols-12 gap-4 h-[calc(100vh-100px)]">
            {/* Sidebar List */}
            <div className="col-span-3 border-r pr-4 overflow-y-auto">
                <div className="flex justify-between items-center mb-4">
                    <h2 className="text-xl font-bold">Prompts</h2>
                    <Button size="sm" onClick={handleCreateNew}><Plus className="w-4 h-4" /></Button>
                </div>
                <div className="space-y-2">
                    {prompts.map(p => (
                        <Card 
                            key={p.id} 
                            className={`cursor-pointer hover:bg-muted/50 ${selectedPrompt?.id === p.id ? 'border-primary' : ''}`}
                            onClick={() => handleSelect(p)}
                        >
                            <CardHeader className="p-3">
                                <div className="flex justify-between">
                                    <span className="font-medium">{p.name}</span>
                                    <Badge variant="secondary">v{p.version}</Badge>
                                </div>
                                <CardDescription className="text-xs truncate">{p.description}</CardDescription>
                            </CardHeader>
                        </Card>
                    ))}
                </div>
            </div>

            {/* Main Editor Area */}
            <div className="col-span-9 flex flex-col h-full">
                {(selectedPrompt || isEditing) ? (
                    <>
                        <div className="flex justify-between items-center mb-4">
                            <div className="flex items-center gap-2">
                                {isEditing ? (
                                    <Input value={editName} onChange={e => setEditName(e.target.value)} className="w-64" placeholder="Prompt Name" disabled={!!selectedPrompt} />
                                ) : (
                                    <h2 className="text-2xl font-bold">{selectedPrompt?.name}</h2>
                                )}
                                {isEditing ? (
                                    <Input value={editDesc} onChange={e => setEditDesc(e.target.value)} className="w-96" placeholder="Description" />
                                ) : (
                                    <span className="text-muted-foreground">{selectedPrompt?.description}</span>
                                )}
                            </div>
                            <div className="flex gap-2">
                                {!isEditing && <Button variant="outline" onClick={() => setIsEditing(true)}><Edit2 className="w-4 h-4 mr-2"/> Edit</Button>}
                                {isEditing && <Button onClick={handleSave}><Save className="w-4 h-4 mr-2"/> Save</Button>}
                            </div>
                        </div>

                        <div className="grid grid-cols-2 gap-4 flex-1 min-h-0">
                            {/* Editor */}
                            <Card className="flex flex-col">
                                <CardHeader className="py-2 border-b bg-muted/20">
                                    <CardTitle className="text-sm font-medium flex items-center"><Code className="w-4 h-4 mr-2"/> Template (Jinja2)</CardTitle>
                                </CardHeader>
                                <div className="flex-1 p-0 overflow-hidden">
                                     <Editor
                                        height="100%"
                                        defaultLanguage="jinja2" // Monaco might default strictly, use plaintext or html if jinja2 missing
                                        language="handlebars" // Close enough for generic braces
                                        theme="vs-dark"
                                        value={isEditing ? editTemplate : (selectedPrompt?.template || "")}
                                        onChange={(val) => isEditing && setEditTemplate(val || "")}
                                        options={{ readOnly: !isEditing, minimap: { enabled: false } }}
                                     />
                                </div>
                            </Card>

                            {/* Preview / Test */}
                            <Card className="flex flex-col">
                                <CardHeader className="py-2 border-b bg-muted/20">
                                    <CardTitle className="text-sm font-medium flex items-center"><Play className="w-4 h-4 mr-2"/> Test Render</CardTitle>
                                </CardHeader>
                                <CardContent className="flex flex-col gap-4 p-4 h-full overflow-hidden">
                                    <div>
                                        <Label>Variables (JSON)</Label>
                                        <div className="h-32 border rounded mt-1 overflow-hidden">
                                            <Editor
                                                height="100%"
                                                language="json"
                                                theme="vs-dark"
                                                value={testVars}
                                                onChange={(val) => setTestVars(val || "{}")}
                                                options={{ minimap: { enabled: false } }}
                                            />
                                        </div>
                                        <Button size="sm" className="mt-2 w-full" onClick={handleRenderTest} disabled={isEditing}>
                                            Render Preview
                                        </Button>
                                    </div>
                                    <div className="flex-1 flex flex-col min-h-0">
                                        <Label>Output</Label>
                                        <div className="flex-1 border rounded bg-muted/10 p-2 whitespace-pre-wrap overflow-y-auto font-mono text-sm mt-1">
                                            {renderResult || "Run render to see output..."}
                                        </div>
                                    </div>
                                </CardContent>
                            </Card>
                        </div>
                    </>
                ) : (
                    <div className="flex items-center justify-center h-full text-muted-foreground">
                        Select a prompt to edit or create a new one.
                    </div>
                )}
            </div>
        </div>
    );
}
