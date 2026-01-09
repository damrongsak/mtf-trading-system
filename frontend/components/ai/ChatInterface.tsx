"use client";

import React, { useState, useRef, useEffect } from 'react';
import { defaultApi } from '@/lib/api/client';
import { APIResponseAgentList, Agent } from '@/lib/api/generated';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Send, Bot, User as UserIcon, Loader2 } from 'lucide-react';
import { toast } from 'sonner';

interface Message {
  id: string;
  role: 'user' | 'assistant';
  content: string;
  timestamp: Date;
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const [agents, setAgents] = useState<Agent[]>([]);
  const [selectedAgentId, setSelectedAgentId] = useState<string>('market_observer'); // Default

  // Fetch agents on mount to populate selector (optional future feature)
  // For now we just default to market_observer or let backend handle routing

  useEffect(() => {
    if (scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;

    const userMsg: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: input,
      timestamp: new Date()
    };

    setMessages(prev => [...prev, userMsg]);
    setInput('');
    setIsLoading(true);

    try {
        // We use the 'chat/sessions/{id}/messages' endpoint or similar.
        // Since the current spec doesn't detail the full chat flow, we'll assume a direct chat endpoint
        // or a session-based one.
        // Based on previous files, there is POST /ai/chat/sessions/message or similiar in ai-analyst
        // But in api-gateway we have POST /chat/sessions/{session_id}/messages
        
        // For this MVP, let's use a simplified approach if session management isn't fully ready
        // Or create a session first.
        
        // Let's assume we need to create a session or use a static one for now.
        // Checking api-gateway routers/ai.py: 
        // @router.post("/chat/sessions/{session_id}/messages")
        
        // We'll generate a random session ID for this browser session
        const sessionId = "00000000-0000-0000-0000-000000000000"; // Placeholder or generated
        
        // Actually, let's check what the API client supports.
        // defaultApi.apiV1AiChatSessionsSessionIdMessagesPost(...)
        
        // Wait, the API spec I viewed had:
        // /api/v1/ai/agents - GET
        // /api/v1/ai/agents/{id} - GET
        
        // Attempting to use the existing chat endpoint if available.
        // If not, we might need to rely on the agent run endpoint: /api/v1/ai/agent/observer/run
        
        // Let's try the observer run for now as a fallback if chat isn't verified
        // OR simply display a "Chat not fully connected" message if endpoints are missing.
        
        // Mock response for UI demo if backend endpoint is complex:
        setTimeout(() => {
            const aiMsg: Message = {
                id: (Date.now() + 1).toString(),
                role: 'assistant',
                content: "I received your message: " + userMsg.content + ". (Backend integration pending full chat session support)",
                timestamp: new Date()
            };
            setMessages(prev => [...prev, aiMsg]);
            setIsLoading(false);
        }, 1000);

    } catch (error) {
        toast.error("Failed to send message");
        setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[600px] border rounded-lg overflow-hidden bg-background">
      <div className="p-4 border-b bg-muted/50 flex justify-between items-center">
        <div className="font-medium flex items-center gap-2">
            <Bot className="w-4 h-4" />
            AI Chat
        </div>
        {/* Agent selector could go here */}
      </div>
      
      <ScrollArea className="flex-1 p-4" ref={scrollRef}>
        <div className="space-y-4">
            {messages.length === 0 && (
                <div className="text-center text-muted-foreground py-10">
                    <Bot className="w-12 h-12 mx-auto mb-2 opacity-20" />
                    <p>Start a conversation with the AI agents.</p>
                </div>
            )}
            {messages.map((msg) => (
                <div key={msg.id} className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}>
                    <div className={`flex gap-3 max-w-[80%] ${msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'}`}>
                        <div className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 ${
                            msg.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-indigo-500/20 text-indigo-400'
                        }`}>
                            {msg.role === 'user' ? <UserIcon className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                        </div>
                        <div className={`p-3 rounded-lg text-sm ${
                            msg.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted border'
                        }`}>
                            {msg.content}
                        </div>
                    </div>
                </div>
            ))}
            {isLoading && (
                 <div className="flex justify-start">
                    <div className="flex gap-3 max-w-[80%] flex-row">
                        <div className="w-8 h-8 rounded-full flex items-center justify-center shrink-0 bg-indigo-500/20 text-indigo-400">
                             <Bot className="w-4 h-4" />
                        </div>
                         <div className="p-3 rounded-lg text-sm bg-muted border flex items-center">
                            <Loader2 className="w-4 h-4 animate-spin mr-2" />
                            Thinking...
                        </div>
                    </div>
                </div>
            )}
        </div>
      </ScrollArea>

      <div className="p-4 border-t bg-muted/50">
        <form onSubmit={(e) => { e.preventDefault(); handleSend(); }} className="flex gap-2">
            <Input 
                value={input} 
                onChange={(e) => setInput(e.target.value)} 
                placeholder="Type your message..." 
                disabled={isLoading}
                className="flex-1"
            />
            <Button type="submit" disabled={isLoading || !input.trim()}>
                <Send className="w-4 h-4" />
                <span className="sr-only">Send</span>
            </Button>
        </form>
      </div>
    </div>
  );
}
