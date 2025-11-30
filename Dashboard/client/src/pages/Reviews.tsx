import { useQuery } from "@tanstack/react-query";
import { Card } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Skeleton } from "@/components/ui/skeleton";
import { ErrorState } from "@/components/ErrorState";
import { CheckCircle2, AlertCircle, MessageSquare } from "lucide-react";
import { formatDistanceToNow } from "date-fns";
import { queryClient } from "@/lib/queryClient";
import type { PullRequest } from "@/lib/api";
import { apiFetch } from "@/lib/apiClient"; //

const sentimentConfig = {
  approved: {
    icon: CheckCircle2,
    label: "Approved",
    color: "text-chart-2",
    bgColor: "bg-chart-2/10",
  },
  changes_requested: {
    icon: AlertCircle,
    label: "Changes Requested",
    color: "text-chart-4",
    bgColor: "bg-chart-4/10",
  },
  commented: {
    icon: MessageSquare,
    label: "Commented",
    color: "text-chart-1",
    bgColor: "bg-chart-1/10",
  },
};

export default function Reviews() {
  // Updated to use apiFetch
  const {
    data: prs,
    isLoading,
    error,
  } = useQuery<PullRequest[]>({
    queryKey: ["/api/pull-requests"],
    queryFn: () => apiFetch("/api/pull-requests"),
  });

  const recentPRs = prs?.slice(0, 10) || [];

  const handleRefresh = () => {
    queryClient.invalidateQueries({ queryKey: ["/api/pull-requests"] });
  };

  return (
    <div className="flex flex-col h-full">
      <div className="flex-1 overflow-auto">
        <div className="max-w-5xl mx-auto p-6 w-full space-y-6">
          <div>
            <h1 className="text-2xl font-semibold text-foreground">
              AI Reviews
            </h1>
            <p className="text-sm text-muted-foreground mt-1">
              Recent pull request activity and reviews
            </p>
          </div>

          {error ? (
            <ErrorState
              title="Failed to load reviews"
              message="Unable to fetch pull request reviews from GitHub. Please try again."
              onRetry={handleRefresh}
            />
          ) : isLoading ? (
            <div className="space-y-3">
              {[1, 2, 3, 4].map((i) => (
                <Skeleton key={i} className="h-32" />
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              {recentPRs.map((pr) => {
                const sentiment = pr.merged
                  ? "approved"
                  : pr.state === "open"
                  ? "commented"
                  : "changes_requested";

                const config =
                  sentimentConfig[sentiment as keyof typeof sentimentConfig];
                const SentimentIcon = config.icon;

                return (
                  <Card
                    key={pr.id}
                    className="p-4"
                    data-testid={`card-review-${pr.id}`}
                  >
                    <div className="flex items-start gap-4">
                      {/* Icon Badge */}
                      <div
                        className={`h-10 w-10 rounded-md ${config.bgColor} flex items-center justify-center shrink-0`}
                      >
                        <SentimentIcon className={`h-5 w-5 ${config.color}`} />
                      </div>

                      {/* Content */}
                      <div className="flex-1 min-w-0">
                        <div className="flex items-start justify-between gap-2 mb-2">
                          <div className="flex-1">
                            <h3 className="text-base font-medium text-card-foreground">
                              #{pr.number} — {pr.title}
                            </h3>
                            <div className="flex items-center gap-2 text-sm text-muted-foreground mt-1">
                              <span>{pr.repository}</span>
                              <span>•</span>
                              <span>
                                {formatDistanceToNow(new Date(pr.updated_at), {
                                  addSuffix: true,
                                })}
                              </span>
                            </div>
                          </div>

                          <Badge variant="secondary">{config.label}</Badge>
                        </div>

                        <p className="text-sm text-muted-foreground">
                          {pr.merged
                            ? "Pull request was successfully merged after review."
                            : pr.state === "open"
                            ? "Pull request is currently open and awaiting review."
                            : "Pull request was closed without merging."}
                        </p>
                      </div>
                    </div>
                  </Card>
                );
              })}
            </div>
          )}

          {!isLoading && !error && recentPRs.length === 0 && (
            <div className="text-center py-12">
              <p className="text-muted-foreground">No reviews available</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
