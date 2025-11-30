import { SiGithub } from "react-icons/si";
import {
  BarChart3,
  FileText,
  FolderGit2,
  GitPullRequest,
  LogOut,
  User,
} from "lucide-react";
import { Link, useLocation } from "wouter";
import { useQuery } from "@tanstack/react-query";
import {
  Sidebar,
  SidebarContent,
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarHeader,
  SidebarFooter,
} from "@/components/ui/sidebar";
import { Avatar, AvatarFallback, AvatarImage } from "@/components/ui/avatar";
import { Button } from "@/components/ui/button";
import { Skeleton } from "@/components/ui/skeleton";
import { apiFetch } from "@/lib/apiClient";

const navItems = [
  { title: "My Repos", url: "/", icon: FolderGit2 },
  { title: "Pull Requests", url: "/pull-requests", icon: GitPullRequest },
  { title: "Reviews", url: "/reviews", icon: FileText },
  { title: "Analytics", url: "/analytics", icon: BarChart3 },
];

export function AppSidebar() {
  const [location] = useLocation();

  // 1. Fetch Real User Data
  const { data: user, isLoading } = useQuery({
    queryKey: ["auth-sidebar"],
    queryFn: () => apiFetch("/api/auth/me"),
    retry: false,
  });

  // 2. Logout Handler
  const handleLogout = () => {
    localStorage.removeItem("github_token");
    window.location.href = "/login";
  };

  return (
    <Sidebar>
      <SidebarHeader className="p-4 border-b border-sidebar-border">
        <div className="flex items-center gap-2">
          <div className="h-8 w-8 rounded-md bg-primary flex items-center justify-center">
            <SiGithub className="h-5 w-5 text-primary-foreground" />
          </div>
          <div className="flex flex-col">
            <span className="text-sm font-semibold text-sidebar-foreground">
              AI PR Review
            </span>
            <span className="text-xs text-muted-foreground">
              Agent Dashboard
            </span>
          </div>
        </div>
      </SidebarHeader>

      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>Navigation</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {navItems.map((item) => {
                const isActive = location === item.url;
                return (
                  <SidebarMenuItem key={item.title}>
                    <SidebarMenuButton
                      asChild
                      isActive={isActive}
                      data-testid={`link-${item.title
                        .toLowerCase()
                        .replace(/\s+/g, "-")}`}
                    >
                      <Link href={item.url}>
                        <item.icon className="h-4 w-4" />
                        <span>{item.title}</span>
                      </Link>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                );
              })}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      </SidebarContent>

      {/* FOOTER: Real User Info + Logout */}
      <SidebarFooter className="p-4 border-t border-sidebar-border">
        {isLoading ? (
          <div className="flex items-center gap-3">
            <Skeleton className="h-8 w-8 rounded-full" />
            <div className="space-y-1">
              <Skeleton className="h-3 w-24" />
              <Skeleton className="h-2 w-16" />
            </div>
          </div>
        ) : user ? (
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-3 min-w-0 overflow-hidden">
              <Avatar className="h-8 w-8 border border-border">
                <AvatarImage src={user.avatar_url} />
                <AvatarFallback>
                  {user.login.substring(0, 2).toUpperCase()}
                </AvatarFallback>
              </Avatar>
              <div className="flex flex-col min-w-0">
                <span className="text-sm font-medium text-sidebar-foreground truncate">
                  {user.name || user.login}
                </span>
                <span className="text-xs text-muted-foreground truncate">
                  @{user.login}
                </span>
              </div>
            </div>

            <Button
              variant="ghost"
              size="icon"
              onClick={handleLogout}
              title="Logout"
              className="h-8 w-8 text-muted-foreground hover:text-destructive shrink-0"
            >
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        ) : (
          // Fallback if data fetch fails but token exists
          <div className="flex items-center justify-between gap-2">
            <div className="flex items-center gap-3">
              <div className="h-8 w-8 rounded-full bg-muted flex items-center justify-center">
                <User className="h-4 w-4" />
              </div>
              <span className="text-sm text-muted-foreground">Guest</span>
            </div>
            <Button variant="ghost" size="icon" onClick={handleLogout}>
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        )}
      </SidebarFooter>
    </Sidebar>
  );
}
