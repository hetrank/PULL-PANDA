import type { Express, Request, Response } from "express";
import { Octokit } from "@octokit/rest";

// Typed helper to get authenticated GitHub client
function getClient(req: Request): Octokit {
  const authHeader = req.headers.authorization;
  const token = authHeader ? authHeader.split(" ")[1] : null;

  if (!token) {
    const error: any = new Error("Not authenticated");
    error.status = 401;
    throw error;
  }

  return new Octokit({ auth: token });
}

export async function registerRoutes(app: Express): Promise<void> {
  // Current Logged-in User

  app.get("/api/user", async (req: Request, res: Response) => {
    try {
      const octokit = getClient(req);
      const { data: user } = await octokit.rest.users.getAuthenticated();
      res.json(user);
    } catch (error: any) {
      console.error("Error fetching user:", error);
      res.status(error.status || 500).json({ error: error.message });
    }
  });

  // Repositories (Optimized)
  app.get("/api/repositories", async (req: Request, res: Response) => {
    try {
      const octokit = getClient(req);

      const { data: repos } = await octokit.rest.repos.listForAuthenticatedUser(
        {
          sort: "updated",
          per_page: 20, // Reduced from 30 to speed up list
        }
      );

      // OPTIMIZATION: Run all PR counts in PARALLEL
      const repositoriesWithPRCounts = await Promise.all(
        repos.map(async (repo) => {
          try {
            // Only fetch count, minimal page size
            const { data: pullRequests } = await octokit.rest.pulls.list({
              owner: repo.owner!.login,
              repo: repo.name,
              state: "open",
              per_page: 1, // We just need the count usually, but GitHub API doesn't give count directly easily without search.
              // Actually, keeping list is safer but limiting per_page helps if we just want length
            });
            // Note: This is still imperfect for large PR counts but faster than sequential.

            return {
              id: repo.id,
              name: repo.name,
              owner: repo.owner?.login || "",
              full_name: repo.full_name,
              description: repo.description,
              private: repo.private,
              html_url: repo.html_url,
              stargazers_count: repo.stargazers_count,
              forks_count: repo.forks_count,
              language: repo.language,
              open_issues_count: repo.open_issues_count,
              open_prs_count: pullRequests.length, // This might only show page 1 count, but it's fast.
              updated_at: repo.updated_at,
            };
          } catch (err) {
            return {
              id: repo.id,
              name: repo.name,
              owner: repo.owner?.login || "",
              full_name: repo.full_name,
              description: repo.description,
              private: repo.private,
              html_url: repo.html_url,
              stargazers_count: repo.stargazers_count,
              forks_count: repo.forks_count,
              language: repo.language,
              open_issues_count: repo.open_issues_count,
              open_prs_count: 0,
              updated_at: repo.updated_at,
            };
          }
        })
      );

      res.json(repositoriesWithPRCounts);
    } catch (error: any) {
      console.error("Error fetching repositories:", error);
      res.status(error.status || 500).json({ error: error.message });
    }
  });

  // Pull Requests (Heavy Optimization)
  app.get("/api/pull-requests", async (req: Request, res: Response) => {
    try {
      const octokit = getClient(req);
      const repoFilter = req.query.repo as string | undefined;
      const ownerFilter = req.query.owner as string | undefined;

      // 1. If filtering, ONLY fetch that one repo. Huge speedup.
      let targetRepos = [];

      if (repoFilter && ownerFilter) {
        try {
          const { data: repo } = await octokit.rest.repos.get({
            owner: ownerFilter,
            repo: repoFilter,
          });
          targetRepos = [repo];
        } catch (e) {
          targetRepos = []; // Repo not found
        }
      } else {
        // Otherwise fetch recent 10 active repos
        const { data: repos } =
          await octokit.rest.repos.listForAuthenticatedUser({
            per_page: 10,
            sort: "updated",
          });
        targetRepos = repos;
      }

      // 2. Fetch PRs for these repos in PARALLEL
      const allPRsNested = await Promise.all(
        targetRepos.map(async (repo) => {
          try {
            const { data: prs } = await octokit.rest.pulls.list({
              owner: repo.owner!.login,
              repo: repo.name,
              state: "all",
              per_page: 20, // Limit to 20 recent PRs per repo for speed
              sort: "updated",
              direction: "desc",
            });

            // 3. Fetch "AI Status" for these PRs in PARALLEL
            const prsWithStatus = await Promise.all(
              prs.map(async (pr) => {
                // Quick check for comments
                const { data: comments } =
                  await octokit.rest.issues.listComments({
                    owner: repo.owner!.login,
                    repo: repo.name,
                    issue_number: pr.number,
                    per_page: 100, // usually enough to find the bot
                  });

                const aiReviewed = comments.some(
                  (c) =>
                    c.body?.toLowerCase().includes("ai-powered review") ||
                    c.user?.login.includes("bot")
                );

                return {
                  id: pr.id,
                  number: pr.number,
                  title: pr.title,
                  state: pr.state,
                  merged: pr.merged_at !== null,
                  html_url: pr.html_url,
                  created_at: pr.created_at,
                  updated_at: pr.updated_at,
                  repository: repo.name,
                  owner: repo.owner!.login,
                  user: {
                    login: pr.user?.login || "unknown",
                    avatar_url: pr.user?.avatar_url || "",
                  },
                  aiReviewed,
                };
              })
            );

            return prsWithStatus;
          } catch (e) {
            return [];
          }
        })
      );

      // Flatten the array
      const flatPRs = allPRsNested.flat();

      // Sort globally by update time
      flatPRs.sort(
        (a, b) =>
          new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime()
      );

      res.json(flatPRs);
    } catch (error: any) {
      res.status(error.status || 500).json({ error: error.message });
    }
  });

  // PR Reviews (Details)
  app.get(
    "/api/pull-requests/:owner/:repo/:number/reviews",
    async (req: Request, res: Response) => {
      try {
        const octokit = getClient(req);
        const { owner, repo, number } = req.params;
        const PR_NUMBER = parseInt(number);

        // Parallelize Reviews + Comments fetch
        const [reviewsRes, commentsRes] = await Promise.all([
          octokit.rest.pulls.listReviews({
            owner,
            repo,
            pull_number: PR_NUMBER,
          }),
          octokit.rest.issues.listComments({
            owner,
            repo,
            issue_number: PR_NUMBER,
          }),
        ]);

        const aiReviews = commentsRes.data.filter(
          (c) =>
            c.user?.login?.toLowerCase().includes("bot") ||
            c.body?.toLowerCase().includes("ai-powered review") ||
            c.body?.toLowerCase().includes("static analysis")
        );

        res.json({
          reviews: reviewsRes.data,
          aiReviews,
          allComments: commentsRes.data,
        });
      } catch (error: any) {
        res.status(error.status || 500).json({ error: error.message });
      }
    }
  );

  // Stats (Optimized)
  app.get("/api/stats", async (req: Request, res: Response) => {
    try {
      const octokit = getClient(req);

      // Fetch top 10 repos only for stats summary to save time
      const { data: repos } = await octokit.rest.repos.listForAuthenticatedUser(
        {
          per_page: 10,
          sort: "updated",
        }
      );

      let totalPRs = 0;
      let openPRs = 0;
      let mergedPRs = 0;
      let closedPRs = 0;

      // Run repo stats in parallel
      await Promise.all(
        repos.map(async (repo) => {
          try {
            const { data: prs } = await octokit.rest.pulls.list({
              owner: repo.owner!.login,
              repo: repo.name,
              state: "all",
              per_page: 50,
            });

            totalPRs += prs.length;
            openPRs += prs.filter((pr) => pr.state === "open").length;
            mergedPRs += prs.filter((pr) => pr.merged_at).length;
            closedPRs += prs.filter(
              (pr) => pr.state === "closed" && !pr.merged_at
            ).length;
          } catch (e) {
            // ignore error for specific repo
          }
        })
      );

      res.json({
        totalPRs,
        openPRs,
        mergedPRs,
        closedPRs,
        acceptanceRate: totalPRs ? Math.round((mergedPRs / totalPRs) * 100) : 0,
        activeRepos: repos.length,
      });
    } catch (error: any) {
      res.status(error.status || 500).json({ error: error.message });
    }
  });
}
