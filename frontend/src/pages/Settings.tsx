import Layout from "@/components/Layout";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Switch } from "@/components/ui/switch";
import { Slider } from "@/components/ui/slider";
import { Save } from "lucide-react";
import { toast } from "sonner";
import { useEffect, useState } from "react";
import { API_BASE } from "@/config";

export default function Settings() {
  const [maxElements, setMaxElements] = useState([100]);
  const [loopLimit, setLoopLimit] = useState([10]);
  const [waitTime, setWaitTime] = useState([3000]);
  const [debugMode, setDebugMode] = useState(false);
  const [autoScreenshot, setAutoScreenshot] = useState(true);
  const [headlessMode, setHeadlessMode] = useState(true);

  useEffect(() => {
    const fetchSettings = async () => {
      const res = await fetch(`${API_BASE}/api/settings`);
      const data = await res.json();
      setMaxElements([data.max_elements]);
      setLoopLimit([data.loop_limit]);
      setWaitTime([data.wait_time]);
      setDebugMode(data.debug_mode);
      setAutoScreenshot(data.auto_screenshot);
      setHeadlessMode(data.headless_mode);
    };
    fetchSettings();
  }, []);

  const handleSave = async () => {
    const payload = {
      max_elements: maxElements[0],
      loop_limit: loopLimit[0],
      wait_time: waitTime[0],
      debug_mode: debugMode,
      auto_screenshot: autoScreenshot,
      headless_mode: headlessMode,
    };

    try {
      const res = await fetch("http://localhost:8000/api/settings", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify(payload),
      });

      if (!res.ok) throw new Error("Failed to save");
      toast.success("Settings saved successfully");
    } catch (err) {
      console.error(err);
      toast.error("Failed to save settings")
    }

  };

  return (
    <Layout>
      {/* Header */}
      <div className="border-b border-border bg-card px-8 py-6">
        <h1 className="text-3xl font-bold mb-2">Settings</h1>
        <p className="text-muted-foreground">
          Configure automation parameters and preferences
        </p>
      </div>

      {/* Content */}
      <div className="flex-1 overflow-y-auto p-8">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Automation Parameters */}
          <Card>
            <CardHeader>
              <CardTitle>Automation Parameters</CardTitle>
              <CardDescription>
                Adjust core settings for agent behavior
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="space-y-2">
                <Label>
                  Max Elements per Query: {maxElements[0]}
                </Label>
                <Slider
                  value={maxElements}
                  onValueChange={setMaxElements}
                  min={10}
                  max={500}
                  step={10}
                  className="w-full"
                />
                <p className="text-xs text-muted-foreground">
                  Maximum number of elements to return in a single DOM query
                </p>
              </div>

              <div className="space-y-2">
                <Label>
                  Loop Limit: {loopLimit[0]}
                </Label>
                <Slider
                  value={loopLimit}
                  onValueChange={setLoopLimit}
                  min={1}
                  max={50}
                  step={1}
                  className="w-full"
                />
                <p className="text-xs text-muted-foreground">
                  Maximum number of action loops before stopping
                </p>
              </div>

              <div className="space-y-2">
                <Label>
                  Default Wait Time: {waitTime[0]}s
                </Label>
                <Slider
                  value={waitTime}
                  onValueChange={setWaitTime}
                  min={1}
                  max={120}
                  step={1}
                  className="w-full"
                />
                <p className="text-xs text-muted-foreground">
                  Time to wait between actions
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Browser Settings */}
          <Card>
            <CardHeader>
              <CardTitle>Browser Settings</CardTitle>
              <CardDescription>
                Configure browser behavior
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Headless Mode</Label>
                  <p className="text-xs text-muted-foreground">
                    Run browser without GUI
                  </p>
                </div>
                <Switch
                  checked={headlessMode}
                  onCheckedChange={setHeadlessMode}
                />
              </div>

              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Auto Screenshot</Label>
                  <p className="text-xs text-muted-foreground">
                    Capture screenshots on each action
                  </p>
                </div>
                <Switch
                  checked={autoScreenshot}
                  onCheckedChange={setAutoScreenshot}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="browser-path">Browser Path (Optional)</Label>
                <Input
                  id="browser-path"
                  placeholder="/path/to/browser"
                  className="font-mono text-sm"
                />
              </div>
            </CardContent>
          </Card>

          {/* Logging Settings */}
          <Card>
            <CardHeader>
              <CardTitle>Logging Settings</CardTitle>
              <CardDescription>
                Control console output verbosity
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-6">
              <div className="flex items-center justify-between">
                <div className="space-y-0.5">
                  <Label>Debug Mode</Label>
                  <p className="text-xs text-muted-foreground">
                    Show detailed debug information
                  </p>
                </div>
                <Switch
                  checked={debugMode}
                  onCheckedChange={setDebugMode}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="log-file">Log File Path (Optional)</Label>
                <Input
                  id="log-file"
                  placeholder="/path/to/logs/agent.log"
                  className="font-mono text-sm"
                />
              </div>
            </CardContent>
          </Card>

          {/* API Settings */}
          <Card>
            <CardHeader>
              <CardTitle>API Configuration</CardTitle>
              <CardDescription>
                Configure external API connections
              </CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label htmlFor="api-key">OpenAI API Key</Label>
                <Input
                  id="api-key"
                  type="password"
                  placeholder="sk-..."
                  className="font-mono text-sm"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="model">Model</Label>
                <Input
                  id="model"
                  placeholder="gpt-4"
                  defaultValue="gpt-4"
                  className="font-mono text-sm"
                />
              </div>
            </CardContent>
          </Card>

          {/* Save Button */}
          <div className="flex justify-end">
            <Button
              size="lg"
              onClick={handleSave}
              className="gradient-primary shadow-glow"
            >
              <Save className="h-5 w-5 mr-2" />
              Save Settings
            </Button>
          </div>
        </div>
      </div>
    </Layout>
  );
}
