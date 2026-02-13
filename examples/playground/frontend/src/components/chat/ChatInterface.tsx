import * as React from "react"
import { Send, Square, Bot, User, Menu, X } from "lucide-react"
import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"
import type { Message } from "@/lib/types"

interface ChatInputProps {
  input: string
  handleInputChange: (e: React.ChangeEvent<HTMLTextAreaElement>) => void
  handleSubmit: (e: React.FormEvent) => void
  isLoading: boolean
  stop: () => void
  disabled?: boolean
}

export function ChatInput({
  input,
  handleInputChange,
  handleSubmit,
  isLoading,
  stop,
  disabled,
}: ChatInputProps) {
  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        if (!isLoading && input.trim()) {
          handleSubmit(e)
        }
      }}
      className="relative flex flex-col gap-2"
    >
      <textarea
        value={input}
        onChange={handleInputChange}
        placeholder="Type a message..."
        className="min-h-[60px] w-full rounded-md border border-input bg-background px-3 py-2 text-sm focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-ring"
        disabled={disabled || isLoading}
        rows={1}
      />
      <div className="absolute bottom-2 right-2">
        {isLoading ? (
          <Button
            type="button"
            size="icon"
            variant="secondary"
            onClick={stop}
            className="h-8 w-8"
          >
            <Square className="h-4 w-4 fill-current" />
          </Button>
        ) : (
          <Button
            type="submit"
            size="icon"
            disabled={!input.trim() || disabled}
            className="h-8 w-8"
          >
            <Send className="h-4 w-4" />
          </Button>
        )}
      </div>
    </form>
  )
}

interface MessageBubbleProps {
  message: Message
}

export function MessageBubble({ message }: MessageBubbleProps) {
  const isUser = message.role === "user"
  const text = message.content
    .filter((c) => c.type === "text")
    .map((c) => c.text)
    .join("")

  return (
    <div className={cn("flex gap-3 px-4", isUser ? "bg-muted/50" : "bg-background")}>
      <div
        className={cn(
          "flex h-8 w-8 shrink-0 items-center justify-center rounded-full",
          isUser ? "bg-primary text-primary-foreground" : "bg-secondary text-secondary-foreground"
        )}
      >
        {isUser ? <User className="h-4 w-4" /> : <Bot className="h-4 w-4" />}
      </div>
      <div className="flex-1 py-2">
        <p className="whitespace-pre-wrap">{text}</p>
      </div>
    </div>
  )
}

interface MessageListProps {
  messages: Message[]
  isLoading: boolean
}

export function MessageList({ messages, isLoading }: MessageListProps) {
  return (
    <div className="flex-1 overflow-y-auto p-4 space-y-4">
      {messages.length === 0 && !isLoading && (
        <div className="flex h-full items-center justify-center">
          <div className="text-center text-muted-foreground">
            <Bot className="mx-auto h-12 w-12 opacity-50" />
            <p className="mt-4 text-lg font-medium">Start a conversation</p>
            <p className="text-sm">Select an agent and send a message</p>
          </div>
        </div>
      )}
      {messages.map((message) => (
        <MessageBubble key={message.id} message={message} />
      ))}
      {isLoading && (
        <div className="flex gap-3 px-4">
          <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-secondary text-secondary-foreground">
            <Bot className="h-4 w-4" />
          </div>
          <div className="flex items-center">
            <div className="flex space-x-1">
              <div className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground" style={{ animationDelay: "0ms" }} />
              <div className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground" style={{ animationDelay: "150ms" }} />
              <div className="h-2 w-2 animate-bounce rounded-full bg-muted-foreground" style={{ animationDelay: "300ms" }} />
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

interface ToolCallListProps {
  toolCalls: Array<{
    id: string
    name: string
    args: string
    result?: string
    status: "loading" | "complete"
  }>
}

export function ToolCallList({ toolCalls }: ToolCallListProps) {
  if (toolCalls.length === 0) return null

  return (
    <div className="space-y-2 px-4">
      {toolCalls.map((toolCall) => (
        <div
          key={toolCall.id}
          className="rounded-lg border bg-card p-3 text-card-foreground shadow-sm"
        >
          <div className="flex items-center gap-2">
            <span className="text-xs">⚡</span>
            <span className="font-mono text-sm font-medium">{toolCall.name}</span>
            {toolCall.status === "loading" && (
              <div className="h-2 w-2 animate-spin rounded-full border border-muted-foreground border-t-current" />
            )}
          </div>
        </div>
      ))}
    </div>
  )
}

interface SidebarProps {
  agents: Array<{ name: string; framework: string; description: string }>
  selectedAgent: string
  onSelectAgent: (name: string) => void
  isOpen: boolean
  onToggle: () => void
}

export function Sidebar({
  agents,
  selectedAgent,
  onSelectAgent,
  isOpen,
  onToggle,
}: SidebarProps) {
  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-background/80 backdrop-blur-sm md:hidden"
          onClick={onToggle}
        />
      )}
      <aside
        className={cn(
          "fixed inset-y-0 left-0 z-50 w-64 transform border-r bg-background transition-transform duration-200 md:relative md:translate-x-0",
          !isOpen && "-translate-x-full"
        )}
      >
        <div className="flex h-16 items-center justify-between border-b px-4">
          <span className="font-semibold">Agents</span>
          <Button variant="ghost" size="icon" className="md:hidden" onClick={onToggle}>
            <X className="h-4 w-4" />
          </Button>
        </div>
        <div className="p-2">
          {agents.map((agent) => (
            <button
              key={agent.name}
              onClick={() => {
                onSelectAgent(agent.name)
                if (window.innerWidth < 768) onToggle()
              }}
              className={cn(
                "w-full rounded-lg p-3 text-left transition-colors hover:bg-accent",
                selectedAgent === agent.name && "bg-accent"
              )}
            >
              <div className="flex items-center gap-2">
                <Bot className="h-4 w-4" />
                <span className="font-medium truncate">{agent.name}</span>
              </div>
              <div className="mt-1 flex items-center gap-2">
                <span className="text-xs text-muted-foreground capitalize">
                  {agent.framework}
                </span>
              </div>
            </button>
          ))}
        </div>
      </aside>
    </>
  )
}

interface HeaderProps {
  onToggleSidebar: () => void
}

export function Header({ onToggleSidebar }: HeaderProps) {
  return (
    <header className="flex h-16 items-center justify-between border-b bg-background px-4">
      <div className="flex items-center gap-2">
        <Button
          variant="ghost"
          size="icon"
          className="md:hidden"
          onClick={onToggleSidebar}
        >
          <Menu className="h-4 w-4" />
        </Button>
        <div className="flex items-center gap-2">
          <Bot className="h-6 w-6" />
          <h1 className="text-lg font-semibold">AG-UI Playground</h1>
        </div>
      </div>
    </header>
  )
}
