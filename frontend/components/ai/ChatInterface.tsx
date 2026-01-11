"use client";

import React, { useState, useRef, useEffect } from 'react';
import { defaultApi } from '@/lib/api/client';
import { createChatSession, sendChatMessage, SendMessageRequest, CreateChatSessionRequest } from '@/lib/api/alpha';
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

  // Session State
  const [sessionId, setSessionId] = useState<string | null>(null);

  // Initialize Session on Mount
  useEffect(() => {
    const initSession = async () => {
        try {
            const res = await createChatSession({ context_type: "general" });
            if (res?.id) {
                setSessionId(res.id);
            }
        } catch (e) {
            console.error("Failed to init chat session", e);
            toast.error("Failed to connect to AI Brain");
        }
    };
    initSession();
  }, []);

  useEffect(() => {
    if (scrollRef.current) {
        scrollRef.current.scrollTop = scrollRef.current.scrollHeight;
    }
  }, [messages]);

  const handleSend = async () => {
    if (!input.trim()) return;

    if (!sessionId) {
        toast.error("Initializing session...");
        return;
    }

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
        const payload: SendMessageRequest = {
            content: userMsg.content,
            // Capture snapshot if we had access to editor state
            // For now, pass empty context
        };

        const aiData = await sendChatMessage(sessionId, payload);
        
        if (aiData) {
            const aiMsg: Message = {
                id: aiData.id || Date.now().toString(),
                role: 'assistant',
                content: aiData.content || "No response content",
                timestamp: new Date(aiData.created_at || Date.now())
            };
            setMessages(prev => [...prev, aiMsg]);
        }
    } catch (error) {
        console.error("Chat error:", error);
        toast.error("Failed to send message: " + (error as any).message);
    } finally {
        setIsLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-[600px] border rounded-lg overflow-hidden bg-background">
      <div className="p-4 border-b bg-muted/50 flex justify-between items-center">
        <div className="font-medium flex items-center gap-2">
            <Bot className="w-4 h-4" />
            AI Chat {sessionId ? <span className="text-xs text-green-500">● Connected</span> : <span className="text-xs text-yellow-500">● Connecting...</span>}
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
                        } whitespace-pre-wrap`}>
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
