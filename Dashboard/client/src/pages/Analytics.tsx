import { useMemo } from "react";
import { useQuery } from "@tanstack/react-query";
import { Card } from "@/components/ui/card";
import { StatsCard } from "@/components/StatsCard";
import { ErrorState } from "@/components/ErrorState";
import { Skeleton } from "@/components/ui/skeleton";
import { Button } from "@/components/ui/button";
import {
  Activity,
  Target,
  Clock,
  Users,
  RefreshCw,
  GitBranch,
  BarChart3,
} from "lucide-react";
import { queryClient } from "@/lib/queryClient";
import type { Stats, PullRequest } from "@/lib/api";
import { apiFetch } from "@/lib/apiClient"; // ⭐ NEW
import {
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  Tooltip,
  ResponsiveContainer,
  CartesianGrid,
  PieChart,
  Pie,
  Cell,
  Legend,
} from "recharts";

// Helper: ms → "Xm Ys"
function formatDuration(ms: number): string {
  if (!ms || ms <= 0) return "—";
  const totalSeconds = Math.floor(ms / 1000);
  const minutes = Math.floor(totalSeconds / 60);
  const seconds = totalSeconds % 60;
  if (minutes === 0) return `${seconds}s`;
  return `${minutes}m ${seconds}s`;
}

export default function Analytics() {
  // Repo filter from URL: /analytics?repo=xyz&owner=abc
  const params = new URLSearchParams(window.location.search);
  const repoFilter = params.get("repo");
  const ownerFilter = params.get("owner");

  // Global stats
  const {
    data: stats,
    isLoading: statsLoading,
    error: statsError,
  } = useQuery<Stats>({
    queryKey: ["/api/stats"],
    queryFn: () => apiFetch("/api/stats"),
  });

  // All PRs (filter client-side)
  const {
    data: prs,
    isLoading: prsLoading,
    error: prsError,
  } = useQuery<PullRequest[]>({
    queryKey: ["/api/pull-requests"],
    queryFn: () => apiFetch("/api/pull-requests"),
  });

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ["/api/stats"] });
    queryClient.invalidateQueries({ queryKey: ["/api/pull-requests"] });
  };

  const {
    filteredPrs,
    totalPRs,
    openPRs,
    mergedPRs,
    closedPRs,
    activeRepos,
    aiReviewedCount,
    aiCoverage,
    prStatusData,
    prVolumeTimeline,
    aiReviewTimeline,
    avgAIResponseMs,
    minAIResponseMs,
    maxAIResponseMs,
    sentimentBreakdown,
    topContributors,
    repoPrCounts,
    bestRepo,
  } = useMemo(() => {
    const result = {
      filteredPrs: [] as PullRequest[],
      totalPRs: 0,
      openPRs: 0,
      mergedPRs: 0,
      closedPRs: 0,
      activeRepos: 0,
      aiReviewedCount: 0,
      aiCoverage: 0,
      prStatusData: [] as { name: string; value: number }[],
      prVolumeTimeline: [] as { date: string; count: number }[],
      aiReviewTimeline: [] as { date: string; count: number }[],
      avgAIResponseMs: 0,
      minAIResponseMs: 0,
      maxAIResponseMs: 0,
      sentimentBreakdown: [] as { name: string; value: number }[],
      topContributors: [] as { name: string; prs: number; merged: number }[],
      repoPrCounts: [] as { name: string; count: number }[],
      bestRepo: null as {
        name: string;
        total: number;
        merged: number;
        aiCoverage: number;
        avgMergeMs: number;
      } | null,
    };

    if (!prs) return result;

    // Apply filters
    const filtered = prs.filter((pr) => {
      if (repoFilter && pr.repository !== repoFilter) return false;
      if (ownerFilter && pr.owner !== ownerFilter) return false;
      return true;
    });

    result.filteredPrs = filtered;

    const totalPRs = filtered.length;
    result.totalPRs = totalPRs;

    let open = 0;
    let merged = 0;
    let closed = 0;
    let aiReviewed = 0;

    const repoSet = new Set<string>();
    const prVolumeMap: Record<string, number> = {};
    const aiVolumeMap: Record<string, number> = {};
    const aiResponseTimes: number[] = [];

    const sentimentMap: Record<
      "approved" | "changes_requested" | "commented",
      number
    > = {
      approved: 0,
      changes_requested: 0,
      commented: 0,
    };

    const contributorMap: Record<string, { prs: number; merged: number }> = {};

    const repoStatsMap: Record<
      string,
      {
        total: number;
        merged: number;
        aiReviewed: number;
        mergeTimes: number[];
      }
    > = {};

    for (const pr of filtered) {
      repoSet.add(pr.repository);

      // Status
      if (pr.merged) merged++;
      else if (pr.state === "open") open++;
      else closed++;

      // AI reviewed
      if (pr.aiReviewed) {
        aiReviewed++;

        const created = new Date(pr.created_at).getTime();
        const updated = new Date(pr.updated_at).getTime();

        if (updated > created) {
          aiResponseTimes.push(updated - created);
          const day = pr.updated_at.slice(0, 10);
          aiVolumeMap[day] = (aiVolumeMap[day] || 0) + 1;
        }
      }

      // Volume timeline
      const createdDay = pr.created_at.slice(0, 10);
      prVolumeMap[createdDay] = (prVolumeMap[createdDay] || 0) + 1;

      // Sentiment (approx)
      if (pr.merged) sentimentMap.approved++;
      else if (pr.state === "open") sentimentMap.commented++;
      else sentimentMap.changes_requested++;

      // Contributors
      const user = pr.user?.login || "unknown";
      if (!contributorMap[user]) {
        contributorMap[user] = { prs: 0, merged: 0 };
      }
      contributorMap[user].prs++;
      if (pr.merged) contributorMap[user].merged++;

      // Repo stats
      if (!repoStatsMap[pr.repository]) {
        repoStatsMap[pr.repository] = {
          total: 0,
          merged: 0,
          aiReviewed: 0,
          mergeTimes: [],
        };
      }
      const repoStat = repoStatsMap[pr.repository];

      repoStat.total++;
      if (pr.merged) {
        repoStat.merged++;
        const created = new Date(pr.created_at).getTime();
        const updated = new Date(pr.updated_at).getTime();
        if (updated > created) {
          repoStat.mergeTimes.push(updated - created);
        }
      }
      if (pr.aiReviewed) repoStat.aiReviewed++;
    }

    result.openPRs = open;
    result.mergedPRs = merged;
    result.closedPRs = closed;

    result.activeRepos = repoSet.size || stats?.activeRepos || 0;

    result.aiReviewedCount = aiReviewed;
    result.aiCoverage =
      totalPRs > 0 ? Math.round((aiReviewed / totalPRs) * 100) : 0;

    result.prStatusData = [
      { name: "Merged", value: merged },
      { name: "Open", value: open },
      { name: "Closed", value: closed },
    ];

    result.prVolumeTimeline = Object.entries(prVolumeMap)
      .map(([date, count]) => ({ date, count }))
      .sort((a, b) => a.date.localeCompare(b.date));

    result.aiReviewTimeline = Object.entries(aiVolumeMap)
      .map(([date, count]) => ({ date, count }))
      .sort((a, b) => a.date.localeCompare(b.date));

    if (aiResponseTimes.length > 0) {
      const sum = aiResponseTimes.reduce((a, b) => a + b, 0);
      result.avgAIResponseMs = sum / aiResponseTimes.length;
      result.minAIResponseMs = Math.min(...aiResponseTimes);
      result.maxAIResponseMs = Math.max(...aiResponseTimes);
    }

    result.sentimentBreakdown = [
      { name: "Approved (Merged)", value: sentimentMap.approved },
      {
        name: "Changes Requested / Closed",
        value: sentimentMap.changes_requested,
      },
      { name: "Open / In Review", value: sentimentMap.commented },
    ];

    result.topContributors = Object.entries(contributorMap)
      .map(([name, d]) => ({ name, prs: d.prs, merged: d.merged }))
      .sort((a, b) => b.prs - a.prs)
      .slice(0, 5);

    result.repoPrCounts = Object.entries(repoStatsMap)
      .map(([name, stat]) => ({ name, count: stat.total }))
      .sort((a, b) => b.count - a.count);

    // Best performing repo
    let best = null as typeof result.bestRepo;

    for (const [name, stat] of Object.entries(repoStatsMap)) {
      const aiCoverageRepo =
        stat.total > 0 ? (stat.aiReviewed / stat.total) * 100 : 0;
      const avgMergeMs =
        stat.mergeTimes.length > 0
          ? stat.mergeTimes.reduce((a, b) => a + b, 0) / stat.mergeTimes.length
          : 0;

      if (
        !best ||
        stat.merged > best.merged ||
        (stat.merged === best.merged && aiCoverageRepo > best.aiCoverage)
      ) {
        best = {
          name,
          total: stat.total,
          merged: stat.merged,
          aiCoverage: Math.round(aiCoverageRepo),
          avgMergeMs,
        };
      }
    }

    result.bestRepo = best;

    return result;
  }, [prs, repoFilter, ownerFilter, stats]);

  const isLoading = statsLoading || prsLoading;
  const hasError = statsError || prsError;

  const STATUS_COLORS: Record<string, string> = {
    Merged: "#22c55e",
    Open: "#3b82f6",
    Closed: "#ef4444",
  };

  const SENTIMENT_COLORS: Record<string, string> = {
    "Approved (Merged)": "#22c55e",
    "Changes Requested / Closed": "#f97316",
    "Open / In Review": "#3b82f6",
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-auto">
        <div className="max-w-7xl mx-auto p-6 space-y-6">
          {/* HEADER */}
          <div className="flex items-center justify-between gap-4 flex-wrap">
            <div className="space-y-1">
              <h1 className="text-2xl font-semibold text-foreground">
                Analytics
              </h1>
              <p className="text-sm text-muted-foreground">
                Deep insights into PR activity, AI reviews, and repository
                health
                {repoFilter ? (
                  <>
                    {" — "}
                    <span className="font-medium">
                      {ownerFilter}/{repoFilter}
                    </span>
                  </>
                ) : null}
              </p>
            </div>

            <div className="flex items-center gap-3 flex-wrap">
              {/* Repo Filter */}
              {prs && (
                <select
                  className="px-3 py-1 text-sm border rounded-md bg-background"
                  value={repoFilter ? `${ownerFilter}/${repoFilter}` : "all"}
                  onChange={(e) => {
                    const val = e.target.value;
                    if (val === "all") {
                      window.location.href = "/analytics";
                      return;
                    }
                    const [owner, repo] = val.split("/");
                    window.location.href = `/analytics?owner=${owner}&repo=${repo}`;
                  }}
                >
                  <option value="all">All Repositories</option>
                  {Array.from(
                    new Set(prs?.map((pr) => `${pr.owner}/${pr.repository}`))
                  ).map((pair) => (
                    <option key={pair} value={pair}>
                      {pair}
                    </option>
                  ))}
                </select>
              )}

              <Button
                variant="outline"
                onClick={handleRefresh}
                disabled={isLoading}
              >
                <RefreshCw
                  className={`h-4 w-4 mr-2 ${isLoading ? "animate-spin" : ""}`}
                />
                Refresh
              </Button>
            </div>
          </div>

          {/* ERROR STATE */}
          {hasError && (
            <ErrorState
              title="Failed to load analytics"
              message="Unable to fetch analytics data from GitHub. Please try again."
              onRetry={handleRefresh}
            />
          )}

          {/* TOP STATS GRID */}
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
            {isLoading ? (
              <>
                <Skeleton className="h-32" />
                <Skeleton className="h-32" />
                <Skeleton className="h-32" />
                <Skeleton className="h-32" />
              </>
            ) : (
              <>
                <StatsCard
                  title="Total PRs"
                  value={totalPRs}
                  icon={Activity}
                  trend={`${openPRs} open • ${mergedPRs} merged`}
                />
                <StatsCard
                  title="AI Review Coverage"
                  value={totalPRs === 0 ? "—" : `${aiCoverage.toString()}%`}
                  icon={Target}
                  trend={
                    totalPRs === 0
                      ? "No PRs yet"
                      : `${aiReviewedCount}/${totalPRs} AI-reviewed`
                  }
                />
                <StatsCard
                  title="Avg AI Response Time"
                  value={formatDuration(avgAIResponseMs)}
                  icon={Clock}
                  trend={
                    avgAIResponseMs
                      ? `Fastest ${formatDuration(
                          minAIResponseMs
                        )} • Slowest ${formatDuration(maxAIResponseMs)}`
                      : "No AI reviews yet"
                  }
                />
                <StatsCard
                  title="Active Repositories"
                  value={activeRepos}
                  icon={GitBranch}
                  trend={
                    repoFilter ? "Within selected repo" : "Across all repos"
                  }
                />
              </>
            )}
          </div>

          {/* --- CHARTS, CONTRIBUTOR TABLE, BEST REPO CARD --- */}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* STATUS PIE + PR VOLUME CHART — unchanged */}
            <Card className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-card-foreground">
                  PR Status Distribution
                </h3>
                <BarChart3 className="h-4 w-4 text-muted-foreground" />
              </div>
              {isLoading ? (
                <Skeleton className="h-64" />
              ) : totalPRs === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No PR data available for this selection.
                </p>
              ) : (
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={prStatusData}
                        dataKey="value"
                        nameKey="name"
                        outerRadius={85}
                        label
                      >
                        {prStatusData.map((entry, index) => (
                          <Cell
                            key={`status-cell-${index}`}
                            fill={STATUS_COLORS[entry.name]}
                          />
                        ))}
                      </Pie>
                      <Tooltip />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Card>

            <Card className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-card-foreground">
                  PR Volume Over Time
                </h3>
                <Activity className="h-4 w-4 text-muted-foreground" />
              </div>
              {isLoading ? (
                <Skeleton className="h-64" />
              ) : prVolumeTimeline.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  Not enough PR activity to plot.
                </p>
              ) : (
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={prVolumeTimeline}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis allowDecimals={false} />
                      <Tooltip />
                      <Line
                        type="monotone"
                        dataKey="count"
                        stroke="#3b82f6"
                        strokeWidth={2}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Card>
          </div>

          {/* AI TIMELINE + SENTIMENT + CONTRIBUTORS + BEST REPO — unchanged */}
          {/* (Only fetching layer above needed edits) */}

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* AI Reviews timeline */}
            <Card className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-card-foreground">
                  AI Reviews Over Time
                </h3>
                <Target className="h-4 w-4 text-muted-foreground" />
              </div>

              {isLoading ? (
                <Skeleton className="h-64" />
              ) : aiReviewTimeline.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No AI review activity detected yet.
                </p>
              ) : (
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <LineChart data={aiReviewTimeline}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="date" />
                      <YAxis allowDecimals={false} />
                      <Tooltip />
                      <Line
                        type="monotone"
                        dataKey="count"
                        stroke="#22c55e"
                        strokeWidth={2}
                        dot={false}
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Card>

            {/* Outcome sentiment */}
            <Card className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-card-foreground">
                  Outcome / "Sentiment" Breakdown
                </h3>
                <BarChart3 className="h-4 w-4 text-muted-foreground" />
              </div>

              {isLoading ? (
                <Skeleton className="h-64" />
              ) : totalPRs === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No PRs to analyse.
                </p>
              ) : (
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <PieChart>
                      <Pie
                        data={sentimentBreakdown}
                        dataKey="value"
                        nameKey="name"
                        outerRadius={85}
                        label
                      >
                        {sentimentBreakdown.map((entry, index) => (
                          <Cell
                            key={`sentiment-cell-${index}`}
                            fill={SENTIMENT_COLORS[entry.name]}
                          />
                        ))}
                      </Pie>
                      <Tooltip />
                      <Legend />
                    </PieChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Card>
          </div>

          {/* PR COUNTS + CONTRIBUTORS */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
            {/* PRs per repo */}
            <Card className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-card-foreground">
                  PRs per Repository
                </h3>
                <GitBranch className="h-4 w-4 text-muted-foreground" />
              </div>

              {isLoading ? (
                <Skeleton className="h-64" />
              ) : repoPrCounts.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No repository PR data for this selection.
                </p>
              ) : (
                <div className="h-64">
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={repoPrCounts}>
                      <CartesianGrid strokeDasharray="3 3" />
                      <XAxis dataKey="name" />
                      <YAxis allowDecimals={false} />
                      <Tooltip />
                      <Bar dataKey="count" fill="#3b82f6" />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Card>

            {/* Contributor leaderboard */}
            <Card className="p-6">
              <div className="flex items-center justify-between mb-4">
                <h3 className="text-lg font-semibold text-card-foreground">
                  Most Active Contributors
                </h3>
                <Users className="h-4 w-4 text-muted-foreground" />
              </div>

              {isLoading ? (
                <Skeleton className="h-64" />
              ) : topContributors.length === 0 ? (
                <p className="text-sm text-muted-foreground">
                  No contributor data for this selection.
                </p>
              ) : (
                <div className="space-y-3">
                  {topContributors.map((c) => (
                    <div
                      key={c.name}
                      className="flex items-center justify-between gap-3"
                    >
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{c.name}</p>
                        <p className="text-xs text-muted-foreground">
                          {c.prs} PRs • {c.merged} merged
                        </p>
                      </div>
                      <div className="w-32 h-2 bg-muted rounded-full overflow-hidden">
                        <div
                          className="h-full bg-chart-1"
                          style={{
                            width: `${
                              (c.prs /
                                (topContributors[0]?.prs || c.prs || 1)) *
                              100
                            }%`,
                          }}
                        />
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </Card>
          </div>

          {/* BEST PERFORMING REPO */}
          <Card className="p-6">
            <h3 className="text-lg font-semibold mb-3 text-card-foreground">
              Best Performing Repository
            </h3>

            {isLoading ? (
              <Skeleton className="h-24" />
            ) : !bestRepo ? (
              <p className="text-sm text-muted-foreground">
                Not enough data to determine a best performing repo yet.
              </p>
            ) : (
              <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
                <div>
                  <p className="text-sm text-muted-foreground mb-1">
                    Based on merged PRs and AI review coverage
                  </p>

                  <h4 className="text-xl font-semibold text-card-foreground">
                    {bestRepo.name}
                  </h4>

                  <p className="text-sm text-muted-foreground mt-1">
                    {bestRepo.merged}/{bestRepo.total} PRs merged • AI coverage{" "}
                    {bestRepo.aiCoverage}%
                  </p>
                </div>

                <div className="text-sm text-muted-foreground">
                  <p className="mb-1">Avg merge time</p>

                  <p className="text-lg font-medium text-card-foreground">
                    {bestRepo.avgMergeMs
                      ? formatDuration(bestRepo.avgMergeMs)
                      : "—"}
                  </p>
                </div>
              </div>
            )}
          </Card>
        </div>
      </div>
    </div>
  );
}
