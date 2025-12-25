'use client';

import React, { useState, useRef, useEffect } from 'react';
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Brain, Send, Eraser, AlertCircle } from "lucide-react";
import { useAIAnalyst } from "@/lib/hooks/useAIAnalyst";
import ReactMarkdown from "react-markdown";
import { cn } from "@/lib/utils";

export function AIAnalystCard() {
  const { messages, loading, error, sendMessage, clearHistory } = useAIAnalyst();
  const [inputValue, setInputValue] = useState("");
  const scrollAreaRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom of chat
  useEffect(() => {
    if (scrollAreaRef.current) {
        scrollAreaRef.current.scrollTop = scrollAreaRef.current.scrollHeight;
    }
  }, [messages, loading]);

  const handleSend = () => {
    if (inputValue.trim()) {
        sendMessage(inputValue);
        setInputValue("");
    }
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Card className="col-span-1 md:col-span-2 lg:col-span-3 flex flex-col h-[500px]">
      <CardHeader className="flex flex-row items-center justify-between py-3 px-4 border-b border-gray-800">
        <CardTitle className="text-sm font-medium flex items-center gap-2">
          <Brain className="h-4 w-4 text-purple-500" />
          AI Market Observer
        </CardTitle>
        <Button 
            variant="ghost" 
            size="sm" 
            className="h-8 w-8 p-0 hover:text-red-400" 
            onClick={clearHistory}
        >
          <Eraser className="h-4 w-4" />
        </Button>
      </CardHeader>
      
      <CardContent className="flex-1 overflow-hidden p-0 relative flex flex-col">
        {/* Chat Area */}
        <div 
            ref={scrollAreaRef}
            className="flex-1 overflow-y-auto p-4 space-y-4 scrollbar-thin scrollbar-thumb-gray-700 scrollbar-track-transparent"
        >
            {messages.map((msg, idx) => (
                <div 
                    key={idx} 
                    className={cn(
                        "flex w-full",
                        msg.role === 'user' ? "justify-end" : "justify-start"
                    )}
                >
                    <div className={cn(
                        "max-w-[85%] rounded-2xl px-4 py-3 text-sm shadow-sm",
                        msg.role === 'user' 
                            ? "bg-blue-600 text-white rounded-br-none" 
                            : "bg-gray-800 text-gray-200 rounded-bl-none border border-gray-700"
                    )}>
                        {msg.role === 'assistant' ? (
                            <div className="prose prose-invert prose-sm max-w-none prose-p:my-1 prose-headings:my-2 prose-ul:my-1">
                                <ReactMarkdown>{msg.content}</ReactMarkdown>
                            </div>
                        ) : (
                            <p>{msg.content}</p>
                        )}
                        <span className="text-[10px] opacity-50 block mt-1 text-right">
                            {msg.timestamp.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'})}
                        </span>
                    </div>
                </div>
            ))}
            
            {loading && (
                <div className="flex justify-start w-full">
                    <div className="bg-gray-800 border border-gray-700 rounded-2xl rounded-bl-none px-4 py-3 max-w-[85%]">
                        <div className="flex space-x-2 items-center h-5">
                            <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce [animation-delay:-0.3s]"></div>
                            <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce [animation-delay:-0.15s]"></div>
                            <div className="w-2 h-2 bg-purple-500 rounded-full animate-bounce"></div>
                        </div>
                    </div>
                </div>
            )}
            
             {error && (
                <div className="flex justify-center w-full my-2">
                    <div className="bg-red-900/40 text-red-300 text-xs px-3 py-1 rounded-full flex items-center gap-1 border border-red-500/30">
                        <AlertCircle className="h-3 w-3" />
                        <span>{error}</span>
                    </div>
                </div>
            )}
        </div>
      </CardContent>

      <CardFooter className="p-3 border-t border-gray-800 bg-gray-900/50">
        <div className="flex w-full items-center gap-2">
            <Input
                value={inputValue}
                onChange={(e) => setInputValue(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about XAU/USD, signals, or market sentiment..."
                className="bg-gray-950 border-gray-700 focus:border-purple-500 h-10"
                disabled={loading}
            />
            <Button 
                onClick={handleSend} 
                disabled={loading || !inputValue.trim()}
                size="icon"
                className="h-10 w-10 shrink-0 bg-purple-600 hover:bg-purple-700"
            >
                <Send className="h-4 w-4" />
            </Button>
        </div>
      </CardFooter>
    </Card>
  );
}
