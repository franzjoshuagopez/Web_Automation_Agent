import Layout from "@/components/Layout";
import StatCard from "@/components/StatCard";
import { useNavigate } from "react-router-dom";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Clock, Target, Activity, AlertCircle, Terminal } from "lucide-react";
import { useEffect, useState } from "react";
import {API_BASE} from "@/config"

interface DashboardStats {
  elements_inspected: number;
  total_runtime: number;
  success_rate: number;
  failed_actions: number;
}

interface RecentActions {
  id: string;
  action: string;
  time: string;
  status: string;
}

export default function Dashboard() {


  const [stats, setStats] = useState<DashboardStats>({
    elements_inspected: 0,
    total_runtime: 0,
    success_rate: 0,
    failed_actions: 0,
  });
  const [recentActions, setRecentAction] = useState<RecentActions[]>([]);

  useEffect(() => {
    const fetchData = async () => {
      const res = await fetch(`${API_BASE}/api/dashboard`);
      const data = await res.json();
      setStats(data.stats);
      setRecentAction(data.recent_actions);
    };
    fetchData();
  }, []);

  const navigate = useNavigate();

  const handleOpenConsole = () => {
    navigate("/console");
  };

  const handleOpenElements = () => {
    navigate("/elements");
  };

  return (
    <Layout>
      {/* Header */}
      <div className="border-b border-border bg-card px-8 py-6">
        <div>
          <h1 className="text-3xl font-bold mb-2">Dashboard</h1>
          <p className="text-muted-foreground">
            Monitor and control your web automation agent
          </p>
        </div>
      </div>

      {/* Main Content */}
      <div className="flex-1 overflow-y-auto p-8">
        <div className="space-y-6 max-w-7xl mx-auto">
          {/* Stats Grid */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
            <StatCard
              title="Elements Inspected"
              value={stats.elements_inspected}
              icon={Target}
              trend={{ value: "TBD", positive: true }}
            />
            <StatCard
              title="Total Runtime"
              value={stats.total_runtime + " minutes"}
              icon={Clock}
              trend={{ value: "TBD", positive: true }}
            />
            <StatCard
              title="Success Rate"
              value={stats.success_rate + "%"}
              icon={Activity}
              trend={{ value: "TBD", positive: true }}
            />
            <StatCard
              title="Failed Actions"
              value={stats.failed_actions}
              icon={AlertCircle}
              trend={{ value: "TBD", positive: true }}
            />
          </div>

          {/* Recent Activity */}
          <Card>
            <CardHeader>
              <CardTitle>Recent Activity</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="space-y-4">
                {recentActions.map((action) => (
                  <div
                    key={action.id}
                    className="flex items-center justify-between p-4 rounded-lg bg-muted/50 hover:bg-muted transition-smooth"
                  >
                    <div className="flex items-center gap-4">
                      <div
                        className={`w-2 h-2 rounded-full ${
                          action.status === "success"
                            ? "bg-success"
                            : "bg-destructive"
                        }`}
                      />
                      <div>
                        <p className="font-medium">{action.action}</p>
                        <p className="text-sm text-muted-foreground">
                          {action.time}
                        </p>
                      </div>
                    </div>
                    <span
                      className={`text-xs font-medium px-3 py-1 rounded-full ${
                        action.status === "success"
                          ? "bg-success/10 text-success"
                          : "bg-destructive/10 text-destructive"
                      }`}
                    >
                      {action.status}
                    </span>
                  </div>
                ))}
              </div>
            </CardContent>
          </Card>

          {/* Quick Actions */}
          <Card>
            <CardHeader>
              <CardTitle>Quick Actions</CardTitle>
            </CardHeader>
            <CardContent>
              <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                <Button variant="outline" className="justify-start h-auto py-4" onClick={handleOpenConsole}>
                  <Terminal className="h-5 w-5 mr-3" />
                  <div className="text-left">
                    <div className="font-medium">Open Console</div>
                    <div className="text-xs text-muted-foreground">
                      View real-time logs
                    </div>
                  </div>
                </Button>
                <Button variant="outline" className="justify-start h-auto py-4" onClick={handleOpenElements}>
                  <Target className="h-5 w-5 mr-3" />
                  <div className="text-left">
                    <div className="font-medium">Inspect Elements</div>
                    <div className="text-xs text-muted-foreground">
                      Browse DOM data
                    </div>
                  </div>
                </Button>
                <Button variant="outline" className="justify-start h-auto py-4" disabled>
                  <Activity className="h-5 w-5 mr-3" />
                  <div className="text-left">
                    <div className="font-medium">View Metrics</div>
                    <div className="text-xs text-muted-foreground">
                      Analyze performance
                    </div>
                  </div>
                </Button>
              </div>
            </CardContent>
          </Card>
        </div>
      </div>
    </Layout>
  );
}
