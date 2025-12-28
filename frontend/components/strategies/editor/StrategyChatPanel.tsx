"use client"

import React, { useState, useRef, useEffect } from 'react';
import { useStrategyChat } from '@/lib/hooks/useStrategyChat';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Send, Plus, MessageSquare, Loader2, Bot, User, Sparkles, Code2, Zap } from 'lucide-react';
import ReactMarkdown from 'react-markdown';
import { cn } from '@/lib/utils';
import { format } from 'date-fns';

interface StrategyChatPanelProps {
  strategyId?: string;
  contextCode?: string;
  className?: string;
}

const SUGGESTIONS = [
    { label: "Analyze Code", prompt: "Analyze this strategy code and identify potential risks.", icon: Code2 },
    { label: "Optimize Parameters", prompt: "Suggest optimal parameter ranges for backtesting.", icon: Zap },
    { label: "Explain Strategy", prompt: "Explain the logic of this strategy in plain English.", icon: Sparkles },
];

export function StrategyChatPanel({ strategyId, contextCode, className }: StrategyChatPanelProps) {
  const { 
    sessions, 
    activeSessionId, 
    setActiveSessionId,
    messages, 
    loading, 
    sending, 
    createSession, 
    sendMessage 
  } = useStrategyChat(strategyId);

  const [inputText, setInputText] = useState('');
  const scrollRef = useRef<HTMLDivElement>(null);
  
  // Auto-scroll to bottom
  useEffect(() => {
     // Using a timeout to ensure DOM update
     setTimeout(() => {
        if (scrollRef.current) {
            const scrollableNode = scrollRef.current.querySelector('[data-radix-scroll-area-viewport]');
            if (scrollableNode) {
                scrollableNode.scrollTop = scrollableNode.scrollHeight;
            }
        }
     }, 100);
  }, [messages]);

  const handleSend = async (text: string = inputText) => {
    if (!text.trim()) return;
    setInputText(''); 
    
    await sendMessage(text, {
        code: contextCode 
    });
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
        e.preventDefault();
        handleSend();
    }
  };

  return (
    <div className={cn("flex flex-col h-full bg-slate-950", className)}>
      {/* Header - Minimalist */}
      <div className="flex items-center justify-between p-4 border-b border-slate-800/50">
        <div className="flex items-center gap-2">
            <div className="h-6 w-6 rounded-md bg-indigo-500/20 flex items-center justify-center">
                 <Bot className="h-3.5 w-3.5 text-indigo-400" />
            </div>
            <span className="font-medium text-sm text-slate-300">Strategy Assistant</span>
        </div>
        <Button 
            variant="ghost" 
            size="icon" 
            onClick={() => createSession()}
            className="h-7 w-7 text-slate-500 hover:text-emerald-400"
            title="New Chat"
        >
            <Plus className="h-4 w-4" />
        </Button>
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-hidden relative" ref={scrollRef}>
         <ScrollArea className="h-full px-4">
            <div className="flex flex-col gap-6 py-4">
                {messages.length === 0 && !loading && (
                    <div className="flex flex-col items-center justify-center min-h-[300px] text-center px-4 space-y-6">
                        <div className="h-12 w-12 rounded-full bg-slate-900 border border-slate-800 flex items-center justify-center mb-2">
                            <Bot className="h-6 w-6 text-slate-600" />
                        </div>
                        <div className="space-y-1">
                            <h4 className="text-slate-200 font-medium">How can I help?</h4>
                            <p className="text-xs text-slate-500 max-w-[200px] mx-auto">I can analyze your Python code, suggest optimizations, and explain concepts.</p>
                        </div>
                        
                        <div className="grid grid-cols-1 gap-2 w-full max-w-[240px]">
                            {SUGGESTIONS.map((s) => (
                                <button 
                                    key={s.label}
                                    onClick={() => handleSend(s.prompt)}
                                    className="flex items-center gap-3 px-3 py-2.5 rounded-lg border border-slate-800 bg-slate-900/50 hover:bg-slate-800 hover:border-slate-700 transition-all text-left group"
                                >
                                    <s.icon className="h-4 w-4 text-indigo-500 group-hover:text-indigo-400" />
                                    <span className="text-xs text-slate-400 group-hover:text-slate-300 flex-1">{s.label}</span>
                                </button>
                            ))}
                        </div>
                    </div>
                )}
                
                {messages.map((msg) => (
                    <div 
                        key={msg.id} 
                        className={cn(
                            "flex flex-col gap-1 max-w-[95%]",
                            msg.role === 'user' ? "self-end items-end" : "self-start items-start"
                        )}
                    >
                         <span className="text-[10px] text-slate-600 px-1">
                             {msg.role === 'user' ? 'You' : 'Assistant'} • {format(new Date(msg.created_at || new Date()), 'HH:mm')}
                         </span>
                         
                        <div className={cn(
                            "rounded-2xl px-4 py-3 text-sm leading-relaxed shadow-sm",
                            msg.role === 'user' 
                                ? "bg-indigo-600 text-white rounded-br-sm" 
                                : "bg-slate-900 border border-slate-800 text-slate-300 rounded-bl-sm"
                        )}>
                            <div className="prose prose-invert prose-xs max-w-none break-words">
                                <ReactMarkdown 
                                    components={{
                                        code({node, className, children, ...props}) {
                                            return <code className={cn("bg-black/30 rounded px-1 py-0.5 font-mono text-[11px]", className)} {...props}>{children}</code>
                                        },
                                        pre({node, children, ...props}) {
                                             return <pre className="bg-black/30 p-2 rounded-lg overflow-x-auto my-2 border border-white/5" {...props}>{children}</pre>
                                        }
                                    }}
                                >
                                    {msg.content}
                                </ReactMarkdown>
                            </div>
                        </div>
                    </div>
                ))}
                
                {sending && (
                    <div className="flex gap-2 self-start items-center ml-1">
                        <div className="flex gap-1">
                             <span className="w-1.5 h-1.5 rounded-full bg-slate-600 animate-bounce" style={{animationDelay: '0ms'}} />
                             <span className="w-1.5 h-1.5 rounded-full bg-slate-600 animate-bounce" style={{animationDelay: '150ms'}} />
                             <span className="w-1.5 h-1.5 rounded-full bg-slate-600 animate-bounce" style={{animationDelay: '300ms'}} />
                        </div>
                        <span className="text-[10px] text-slate-600">Thinking...</span>
                    </div>
                )}
            </div>
         </ScrollArea>
      </div>

      {/* Input Area */}
      <div className="p-4 bg-slate-950">
        <div className="relative group">
            <Input
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about your strategy..."
                className="pr-12 bg-slate-900 border-slate-800 text-slate-200 placeholder:text-slate-600 focus:border-indigo-500/50 focus:ring-1 focus:ring-indigo-900 transition-all rounded-xl h-11"
            />
            <Button 
                size="icon" 
                variant="ghost" 
                className={cn(
                    "absolute right-1 top-1 h-9 w-9 transition-colors",
                    inputText.trim() 
                        ? "text-emerald-400 hover:text-emerald-300 hover:bg-emerald-400/10" 
                        : "text-slate-600"
                )}
                onClick={() => handleSend()}
                disabled={!inputText.trim() || sending}
            >
                <Send className="h-4 w-4" />
            </Button>
        </div>
        {contextCode && (
             <div className="flex justify-end mt-2">
                 <div className="flex items-center gap-1.5 px-2 py-1 rounded-full bg-emerald-500/5 border border-emerald-500/10 text-[10px] text-emerald-500/70">
                    <Code2 className="h-3 w-3" />
                    <span>Context Active</span>
                 </div>
             </div>
        )}
      </div>
    </div>
  );
}
