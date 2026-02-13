import { useCallback, useRef, useState } from "react"
import type {
  Message,
  MessageRole,
  TextMessageStartEvent,
  TextMessageContentEvent,
  ToolCallStartEvent,
  ToolCallArgsEvent,
  ToolCallResultEvent,
  ThinkingTextMessageContentEvent,
  RunErrorEvent,
} from "@/lib/types"

export interface UseAGUIChatOptions {
  agentName: string
  threadId?: string
  baseUrl?: string
}

export interface ToolCall {
  id: string
  name: string
  args: string
  result?: string
  status: "loading" | "complete"
}

export interface UseAGUIChatReturn {
  messages: Message[]
  input: string
  setInput: (value: string) => void
  isLoading: boolean
  error: string | null
  sendMessage: (content: string) => Promise<void>
  threadId: string | null
  stop: () => void
  toolCalls: ToolCall[]
}

function parseSSEEvent(line: string): Record<string, unknown> | null {
  if (!line.startsWith("data:")) return null
  const data = line.slice(5).trim()
  if (!data) return null
  try {
    return JSON.parse(data)
  } catch {
    return null
  }
}

export function useAGUIChat({
  agentName,
  threadId: initialThreadId,
  baseUrl = "",
}: UseAGUIChatOptions): UseAGUIChatReturn {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState("")
  const [isLoading, setIsLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [threadId, setThreadId] = useState<string | null>(initialThreadId || null)
  const [toolCalls, setToolCalls] = useState<ToolCall[]>([])
  const abortControllerRef = useRef<AbortController | null>(null)

  const stop = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort()
      abortControllerRef.current = null
      setIsLoading(false)
    }
  }, [])

  const sendMessage = useCallback(
    async (content: string) => {
      const currentThreadId = threadId
      const userMessage: Message = {
        id: crypto.randomUUID(),
        role: "user",
        content: [{ type: "text", text: content }],
      }

      setMessages((prev) => [...prev, userMessage])
      setInput("")
      setIsLoading(true)
      setError(null)
      setToolCalls([])

      abortControllerRef.current = new AbortController()

      try {
        const response = await fetch(
          `${baseUrl}/api/agents/${agentName}/`,
          {
            method: "POST",
            headers: {
              "Content-Type": "application/json",
              Accept: "text/event-stream",
            },
            body: JSON.stringify({
              thread_id: currentThreadId,
              run_id: crypto.randomUUID(),
              messages: [
                {
                  role: "user",
                  content: [{ type: "text", text: content }],
                },
              ],
            }),
            signal: abortControllerRef.current.signal,
          }
        )

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }

        if (!response.body) {
          throw new Error("No response body")
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ""

        let currentMessageId: string | null = null

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          buffer += decoder.decode(value, { stream: true })
          const lines = buffer.split("\n")
          buffer = lines.pop() || ""

          for (const line of lines) {
            const event = parseSSEEvent(line)
            if (!event) continue

            const eventType = event.type as string

            switch (eventType) {
              case "run_started": {
                if (event.thread_id && !currentThreadId) {
                  setThreadId(event.thread_id as string)
                }
                break
              }

              case "text_message_start": {
                const textEvent = event as unknown as TextMessageStartEvent
                currentMessageId = textEvent.message_id
                const newMessage: Message = {
                  id: textEvent.message_id,
                  role: textEvent.role,
                  content: [],
                  createdAt: new Date().toISOString(),
                }
                setMessages((prev) => [...prev, newMessage])
                break
              }

              case "text_message_content": {
                const textEvent = event as unknown as TextMessageContentEvent
                if (currentMessageId === textEvent.message_id) {
                  setMessages((prev) =>
                    prev.map((msg) =>
                      msg.id === textEvent.message_id
                        ? {
                            ...msg,
                            content: [
                              ...msg.content,
                              { type: "text", text: textEvent.delta },
                            ],
                          }
                        : msg
                    )
                  )
                }
                break
              }

              case "text_message_end": {
                currentMessageId = null
                break
              }

              case "tool_call_start": {
                const toolEvent = event as unknown as ToolCallStartEvent
                setToolCalls((prev) => [
                  ...prev,
                  {
                    id: toolEvent.tool_call_id,
                    name: toolEvent.tool_call_name,
                    args: "",
                    status: "loading",
                  },
                ])
                break
              }

              case "tool_call_args": {
                const toolEvent = event as unknown as ToolCallArgsEvent
                setToolCalls((prev) =>
                  prev.map((tc) =>
                    tc.id === toolEvent.tool_call_id
                      ? { ...tc, args: tc.args + toolEvent.delta }
                      : tc
                  )
                )
                break
              }

              case "tool_call_end": {
                break
              }

              case "tool_call_result": {
                const toolEvent = event as unknown as ToolCallResultEvent
                setToolCalls((prev) =>
                  prev.map((tc) =>
                    tc.id === toolEvent.tool_call_id
                      ? { ...tc, result: toolEvent.content, status: "complete" }
                      : tc
                  )
                )
                break
              }

              case "thinking_text_message_content": {
                const thinkEvent = event as unknown as ThinkingTextMessageContentEvent
                setMessages((prev) => {
                  const lastMsg = prev[prev.length - 1]
                  if (lastMsg && lastMsg.role === "assistant") {
                    return prev.map((msg, idx) =>
                      idx === prev.length - 1
                        ? {
                            ...msg,
                            content: [
                              ...msg.content,
                              { type: "text", text: thinkEvent.delta },
                            ],
                          }
                        : msg
                    )
                  }
                  return prev
                })
                break
              }

              case "run_error": {
                const errorEvent = event as unknown as RunErrorEvent
                setError(errorEvent.message)
                break
              }
            }
          }
        }
      } catch (err) {
        if ((err as Error).name !== "AbortError") {
          setError((err as Error).message)
        }
      } finally {
        setIsLoading(false)
        abortControllerRef.current = null
      }
    },
    [agentName, threadId, baseUrl]
  )

  return {
    messages,
    input,
    setInput,
    isLoading,
    error,
    sendMessage,
    threadId,
    stop,
    toolCalls,
  }
}
