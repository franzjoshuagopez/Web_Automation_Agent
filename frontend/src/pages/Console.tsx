import { useEffect, useRef, useState } from "react";
import Layout from "@/components/Layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card } from "@/components/ui/card";
import { ScrollArea } from "@/components/ui/scroll-area";
import { Play, Square, Trash2 } from "lucide-react";
import { toast } from "sonner";

interface LogEntry {
  id: number;
  timestamp: string;
  type: "info" | "success" | "error" | "tool";
  message: string;
  details?: string;
}

const WS_URL = (import.meta.env.VITE_WS_URL as string | undefined) || "ws://localhost:8000/ws/chat";

export default function Console() {
  const [goal, setGoal] = useState("");
  const [isRunning, setIsRunning] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([
    {
      id: 1,
      timestamp: new Date().toLocaleTimeString(),
      type: "info",
      message: "Agent UI ready",
    },
  ]);

  const wsRef = useRef<WebSocket | null>(null);
  const nextIdRef = useRef<number>(logs.length + 1);

  const pushLog = (entry: Omit<LogEntry, "id" | "timestamp">) => {
    const id = nextIdRef.current++;
    const timestamp = new Date().toLocaleTimeString();
    setLogs((prev) => [
      ...prev,
      {
        id,
        timestamp,
        ...entry,
      },
    ]);
  };

  useEffect(() => {
    const ws = new WebSocket(WS_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      pushLog({type: "info", message: `Connected to the backend (${WS_URL})` });
    };

    ws.onmessage = (ev) => {
      const text = typeof ev.data === "string" ? ev.data : String(ev.data);

      let type: LogEntry["type"] = "info";
      if (text.toLowerCase().includes("error") || text.toLowerCase().includes("fail")) {
        type = "error";
      }
      else if (text.toLowerCase().includes("tool") || text.toLowerCase().includes("clicked")){
        type = "tool"
      }
      else if (text.toLowerCase().includes("completed") || text.toLowerCase().includes("success")){
        type = "success"
      }

      pushLog({ type, message: text});
      
      if (/(completed|done|success|satisfied)/i.test(text)) {
        setIsRunning(false);
      }
    };

    ws.onclose = (ev) => {
      pushLog({type: "info", message: `WebSocket closed (code=${ev.code})`,});
      wsRef.current = null;
      setIsRunning(false);
    };

    ws.onerror = (err) => {
      pushLog({type: "error", message: "WebSocket error - check backend"});
    };

    return () => {
      try {
        ws.close();
      } catch (e) {

      }
      wsRef.current = null;
    };

  }, []);;

  const handleRun = () => {
    if (!goal.trim()) {
      toast.error("Please enter a goal");
      return;
    }

    if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
      toast.error("Not connected to backend. Retry in a moment.");
      pushLog({type: "error", message: "Socket not open - cannot send goal"});
      return;
    }

    setIsRunning(true);
    pushLog({type: "info", message: `Executing goal: ${goal}`});
    toast.success("Agent execution started");

    try {
      wsRef.current.send(goal);
    } catch (e) {
      pushLog({type: "error", message: `Failed to send goal: ${String(e)}`});
      setIsRunning(false);
    }
  };

  const handleStop = () => {
    setIsRunning(false);
    pushLog({type: "error", message: "Agent execution stopped by user"});
    toast.warning("Agent stopped");
  };

  const handleClear = () => {
    setLogs([]);
    nextIdRef.current = 1;
    setGoal("");
    toast.success("Console cleared");
  };

  const getLogColor = (type: LogEntry["type"]) => {
    switch (type) {
      case "success":
        return "text-success";
      case "error":
        return "text-destructive";
      case "tool":
        return "text-primary";
      default:
        return "text-console-text";
    }
  };

  return (
    <Layout>
      {/* Header */}
      <div className="border-b border-border bg-card px-8 py-6">
        <h1 className="text-3xl font-bold mb-2">Automation Console</h1>
        <p className="text-muted-foreground">
          Real-time execution logs and control panel
        </p>
      </div>

      {/* Console Content */}
      <div className="flex-1 overflow-hidden p-8">
        <div className="h-full max-w-7xl mx-auto space-y-6">
          {/* Goal Input */}
          <Card className="p-6">
            <div className="flex gap-4">
              <Input
                placeholder="Enter automation goal (e.g., 'Sign up on Instagram')"
                value={goal}
                onChange={(e) => setGoal(e.target.value)}
                onKeyDown={(e) => e.key === "Enter" && !isRunning && handleRun()}
                disabled={isRunning}
                className="flex-1 text-base"
              />
              {isRunning ? (
                <Button onClick={handleStop} variant="destructive" size="lg">
                  <Square className="h-5 w-5 mr-2" />
                  Stop
                </Button>
              ) : (
                <Button onClick={handleRun} size="lg" className="gradient-primary">
                  <Play className="h-5 w-5 mr-2" />
                  Run Goal
                </Button>
              )}
              <Button onClick={handleClear} variant="outline" size="lg">
                <Trash2 className="h-5 w-5" />
              </Button>
            </div>
          </Card>

          {/* Console Panel */}
          <Card className="flex-1 console-panel overflow-hidden">
            <div className="p-4 border-b border-console-border flex items-center justify-between">
              <div className="flex items-center gap-2">
                <div className="w-3 h-3 rounded-full bg-destructive" />
                <div className="w-3 h-3 rounded-full bg-warning" />
                <div className="w-3 h-3 rounded-full bg-success" />
                <span className="ml-4 text-sm font-mono font-medium">
                  Agent Output
                </span>
              </div>
              <span className="text-xs text-muted-foreground">
                {logs.length} entries
              </span>
            </div>

            <ScrollArea className="h-[calc(100vh-400px)] p-4">
              <div className="space-y-2 font-mono text-sm">
                {logs.length === 0 ? (
                  <div className="text-center py-12 text-muted-foreground">
                    No logs yet. Run a goal to see execution output.
                  </div>
                ) : (
                  logs.map((log) => (
                    <div
                      key={log.id}
                      className="p-3 rounded bg-console-bg/50 border border-console-border hover:bg-console-bg/70 transition-smooth"
                    >
                      <div className="flex items-start gap-3">
                        <span className="text-muted-foreground text-xs">
                          {log.timestamp}
                        </span>
                        <span
                          className={`font-medium uppercase text-xs ${getLogColor(
                            log.type
                          )}`}
                        >
                          [{log.type}]
                        </span>
                        <span className="flex-1 whitespace-pre-wrap break-words">{log.message}</span>
                      </div>
                      {log.details && (
                        <div className="mt-2 ml-24 text-xs text-muted-foreground">
                          {log.details}
                        </div>
                      )}
                    </div>
                  ))
                )}
              </div>
            </ScrollArea>
          </Card>
        </div>
      </div>
    </Layout>
  );
}
