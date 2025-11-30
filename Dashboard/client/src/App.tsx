import { Switch, Route, useLocation } from "wouter";
import { useQuery, QueryClientProvider } from "@tanstack/react-query";
import { queryClient } from "./lib/queryClient";

import { TooltipProvider } from "@/components/ui/tooltip";
import { ThemeProvider } from "@/components/ThemeProvider";
import { Toaster } from "@/components/ui/toaster";

// UI Components
import { SidebarProvider, SidebarTrigger } from "@/components/ui/sidebar";
import { AppSidebar } from "@/components/AppSidebar";
import { ThemeToggle } from "@/components/ThemeToggle";

// Pages
import Dashboard from "@/pages/Dashboard";
import PullRequests from "@/pages/PullRequests";
import Reviews from "@/pages/Reviews";
import Analytics from "@/pages/Analytics";
import PRDetails from "@/pages/PRDetails";
import NotFound from "@/pages/not-found";
import Login from "@/pages/Login";

import ProtectedRoute from "./ProtectedRoute";
import "./index.css";

import { useEffect, useState } from "react";

export default function App() {
  const [location, setLocation] = useLocation();
  const [isAuthReady, setIsAuthReady] = useState(false);

  // 1. Auth Logic & Redirects
  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const urlToken = params.get("token");

    // Case A: Just logged in via GitHub (Token in URL)
    if (urlToken) {
      console.log("Token found in URL. Saving...");
      localStorage.setItem("github_token", urlToken);
      window.history.replaceState({}, document.title, window.location.pathname);
      setLocation("/");
    }
    // Case B: No token found storage, and not on login page
    else if (!localStorage.getItem("github_token") && location !== "/login") {
      setLocation("/login");
    }

    setIsAuthReady(true);
  }, [location, setLocation]);

  // Guard 1: App is still initializing auth state
  if (!isAuthReady) {
    return (
      <div className="flex h-screen items-center justify-center bg-background text-foreground">
        Loading...
      </div>
    );
  }

  const isLoginPage = location === "/login";
  const storedToken = localStorage.getItem("github_token");

  //Guard 2: Prevent sidebar flash if we are about to redirect to login
  if (!isLoginPage && !storedToken) {
    return (
      <div className="flex h-screen items-center justify-center bg-background text-foreground">
        Redirecting...
      </div>
    );
  }

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <ThemeProvider defaultTheme="dark">
          {isLoginPage ? (
            <Switch>
              <Route path="/login" component={Login} />
            </Switch>
          ) : (
            <SidebarProvider>
              <div className="flex h-screen w-full">
                {/* SIDEBAR */}
                <AppSidebar />

                <div className="flex flex-col flex-1 min-w-0">
                  {/* HEADER */}
                  <header className="flex items-center justify-between px-6 py-3 border-b border-border shrink-0 bg-background">
                    <SidebarTrigger />
                    <ThemeToggle />
                  </header>

                  {/* CONTENT */}
                  <main className="flex-1 overflow-hidden overflow-y-auto">
                    <Switch>
                      <Route
                        path="/"
                        component={() => (
                          <ProtectedRoute>
                            <Dashboard />
                          </ProtectedRoute>
                        )}
                      />
                      <Route
                        path="/pull-requests"
                        component={() => (
                          <ProtectedRoute>
                            <PullRequests />
                          </ProtectedRoute>
                        )}
                      />
                      <Route
                        path="/pr-details/:owner/:repo/:number"
                        component={() => (
                          <ProtectedRoute>
                            <PRDetails />
                          </ProtectedRoute>
                        )}
                      />
                      <Route
                        path="/reviews"
                        component={() => (
                          <ProtectedRoute>
                            <Reviews />
                          </ProtectedRoute>
                        )}
                      />
                      <Route
                        path="/analytics"
                        component={() => (
                          <ProtectedRoute>
                            <Analytics />
                          </ProtectedRoute>
                        )}
                      />
                      <Route component={NotFound} />
                    </Switch>
                  </main>
                </div>
              </div>
            </SidebarProvider>
          )}
          <Toaster />
        </ThemeProvider>
      </TooltipProvider>
    </QueryClientProvider>
  );
}
