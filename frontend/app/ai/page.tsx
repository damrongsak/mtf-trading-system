import { PromptEditor } from '@/components/ai/PromptEditor';
import { AgentList } from '@/components/ai/AgentList';
import { ChatInterface } from '@/components/ai/ChatInterface';
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs"

export default function AIWorkspacePage() {
  return (
    <div className="container mx-auto p-6 max-h-screen overflow-hidden flex flex-col">
      <div className="mb-6">
        <h1 className="text-3xl font-bold tracking-tight">AI Studio</h1>
        <p className="text-muted-foreground">Manage your AI Agents, Prompts, and Personas.</p>
      </div>

      <Tabs defaultValue="prompts" className="flex-1 flex flex-col min-h-0">
        <TabsList>
          <TabsTrigger value="prompts">Prompts</TabsTrigger>
          <TabsTrigger value="agents">Agents</TabsTrigger>
          <TabsTrigger value="chat">Chat</TabsTrigger>
        </TabsList>
        <TabsContent value="prompts" className="flex-1 min-h-0 mt-4">
          <PromptEditor />
        </TabsContent>
        <TabsContent value="agents" className="flex-1 min-h-0 mt-4 overflow-y-auto">
          <AgentList />
        </TabsContent>
        <TabsContent value="chat" className="flex-1 min-h-0 mt-4">
          <ChatInterface />
        </TabsContent>
      </Tabs>
    </div>
  )
}
