import { Link, useLocation } from "wouter";
import { Button } from "@/components/ui/button";
import { useQuery } from "@tanstack/react-query";
import { apiFetch } from "@/lib/apiClient";

export default function Navbar() {
  const [location, setLocation] = useLocation();

  // Fetch logged-in user info (but NOT on login page)
  const { data: user } = useQuery({
    queryKey: ["auth"],
    queryFn: () => apiFetch("/api/auth/me"),
    retry: false,
    enabled: location !== "/login",
  });

  const handleLogout = async () => {
    await apiFetch("/api/auth/logout", {
      method: "POST",
    });

    setLocation("/login");
  };

  const navItems = [
    { label: "Dashboard", path: "/" },
    { label: "Pull Requests", path: "/pull-requests" },
    { label: "Reviews", path: "/reviews" },
    { label: "Analytics", path: "/analytics" },
  ];

  // No navbar on login page
  if (location === "/login") return null;

  return (
    <nav className="w-full bg-[#0d1117] border-b border-gray-800 px-6 py-3 flex items-center justify-between">
      {/* LEFT SIDE — NAV LINKS */}
      <div className="flex items-center gap-6">
        <h1
          onClick={() => setLocation("/")}
          className="text-lg font-semibold text-white cursor-pointer"
        >
          PR Review Agent
        </h1>

        <div className="flex items-center gap-4">
          {navItems.map((item) => (
            <Link key={item.path} href={item.path}>
              <span
                className={`cursor-pointer text-sm px-2 py-1 rounded-md ${
                  location === item.path
                    ? "bg-gray-800 text-white"
                    : "text-gray-400 hover:text-white hover:bg-gray-800"
                }`}
              >
                {item.label}
              </span>
            </Link>
          ))}
        </div>
      </div>

      {/* RIGHT SIDE — USER + LOGOUT */}
      <div className="flex items-center gap-4">
        {user && (
          <div className="flex items-center gap-2">
            <img
              src={user.avatar_url}
              alt="avatar"
              className="w-8 h-8 rounded-full border border-gray-700"
            />
            <span className="text-sm text-gray-300">{user.login}</span>
          </div>
        )}

        <Button variant="destructive" size="sm" onClick={handleLogout}>
          Logout
        </Button>
      </div>
    </nav>
  );
}
