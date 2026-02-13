import { useEffect, useState } from "react"
import { ThemeProvider } from "@/hooks/useTheme"
import { useAGUIChat } from "@/hooks/useAGUIChat"
import { fetchAgents, type Agent } from "@/lib/api"
import { Header, Sidebar, MessageList, ChatInput, ToolCallList } from "@/components/chat/ChatInterface"
import { ThemeToggle } from "@/components/theme-toggle"

function Playground() {
  const [agents, setAgents] = useState<Agent[]>([])
  const [selectedAgent, setSelectedAgent] = useState<string>("")
  const [sidebarOpen, setSidebarOpen] = useState(false)

  const {
    messages,
    input,
    setInput,
    isLoading,
    error,
    sendMessage,
    stop,
    toolCalls,
  } = useAGUIChat({
    agentName: selectedAgent,
  })

  useEffect(() => {
    fetchAgents()
      .then((data) => {
        setAgents(data)
        if (data.length > 0) {
          setSelectedAgent(data[0].name)
        }
      })
      .catch(console.error)
  }, [])

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (input.trim()) {
      sendMessage(input)
    }
  }

  return (
    <div className="flex h-screen flex-col bg-background">
      <Header onToggleSidebar={() => setSidebarOpen(!sidebarOpen)} />
      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          agents={agents}
          selectedAgent={selectedAgent}
          onSelectAgent={setSelectedAgent}
          isOpen={sidebarOpen}
          onToggle={() => setSidebarOpen(!sidebarOpen)}
        />
        <main className="flex flex-1 flex-col overflow-hidden">
          <MessageList messages={messages} isLoading={isLoading} />
          {toolCalls.length > 0 && <ToolCallList toolCalls={toolCalls} />}
          {error && (
            <div className="mx-4 mb-2 rounded-lg bg-destructive/10 p-3 text-sm text-destructive">
              {error}
            </div>
          )}
          <div className="border-t bg-background p-4">
            <ChatInput
              input={input}
              handleInputChange={(e) => setInput(e.target.value)}
              handleSubmit={handleSubmit}
              isLoading={isLoading}
              stop={stop}
              disabled={!selectedAgent}
            />
          </div>
        </main>
      </div>
    </div>
  )
}

export default function App() {
  return (
    <ThemeProvider>
      <Playground />
    </ThemeProvider>
  )
}
