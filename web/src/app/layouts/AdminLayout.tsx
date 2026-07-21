import { Avatar, Button } from "@douyinfe/semi-ui";
import { Box, Boxes, FolderKanban, LogOut, MessageSquareCode, Network, Server, Settings, ShieldCheck, Users } from "lucide-react";
import { ReactNode, Suspense, useCallback, useEffect, useMemo, useState } from "react";
import { NavLink, Outlet, useLocation, useNavigate, useOutletContext } from "react-router-dom";
import { SessionList } from "../../features/playground/SessionList";
import { useAgentSessionContext } from "../../features/playground/AgentSessionProvider";
import { useAuth } from "../../shared/auth/AuthProvider";
import { cx } from "../../shared/lib/className";
import { UI_TEXT } from "../../shared/lib/uiText";
import daybreakLogo from "../../assets/z3r0-logo.png";
import { preloadAdminRoute, preloadAdminRoutes } from "../routePreload";

type AdminLayoutContext = {
  setHeaderActions: (actions: ReactNode) => void;
  refreshWorkProjects: () => void;
};

export function useAdminHeaderActions() {
  return useOutletContext<AdminLayoutContext>().setHeaderActions;
}

export function useRefreshWorkProjects() {
  return useOutletContext<AdminLayoutContext>().refreshWorkProjects;
}

const navItems = [
  { path: "/playground", label: UI_TEXT.navPlayground, eyebrow: UI_TEXT.navPlaygroundEyebrow, icon: MessageSquareCode },
  { path: "/work-projects", label: UI_TEXT.navWorkProjects, eyebrow: UI_TEXT.navWorkProjectsEyebrow, icon: FolderKanban, adminOnly: true },
  { path: "/poc-verifications", label: "PoC 验证", eyebrow: "漏洞复测", icon: ShieldCheck, adminOnly: true },
  { path: "/hosts", label: UI_TEXT.navHosts, eyebrow: UI_TEXT.navHostsEyebrow, icon: Server, adminOnly: true },
  { path: "/egress-proxies", label: UI_TEXT.navEgressProxies, eyebrow: UI_TEXT.navEgressProxiesEyebrow, icon: Network, adminOnly: true },
  { path: "/sandbox-images", label: UI_TEXT.navSandboxImages, eyebrow: UI_TEXT.navSandboxImagesEyebrow, icon: Boxes, adminOnly: true },
  { path: "/sandbox-containers", label: UI_TEXT.navSandboxContainers, eyebrow: UI_TEXT.navSandboxContainersEyebrow, icon: Box, adminOnly: true },
  { path: "/system-users", label: UI_TEXT.navSystemUsers, eyebrow: UI_TEXT.navSystemUsersEyebrow, icon: Users, adminOnly: true },
  { path: "/system-config", label: UI_TEXT.navSystemConfig, eyebrow: UI_TEXT.navSystemConfigEyebrow, icon: Settings, adminOnly: true },
];

export function AdminLayout() {
  const { signOut, user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [headerActions, setHeaderActionsState] = useState<ReactNode>(null);
  const [projectListVersion, setProjectListVersion] = useState(0);
  const {
    sessions,
    sessionsLoading,
    activeSessionId,
    selectSession,
    deleteSession,
    refreshSessions,
    dropSessionRuntime,
    syncSessionSummaries,
  } = useAgentSessionContext();

  const setHeaderActions = useCallback((actions: ReactNode) => {
    setHeaderActionsState((current) => (Object.is(current, actions) ? current : actions));
  }, []);

  useEffect(() => {
    const id = window.setTimeout(preloadAdminRoutes, 300);
    return () => window.clearTimeout(id);
  }, []);

  const refreshWorkProjects = useCallback(() => {
    setProjectListVersion((version) => version + 1);
  }, []);

  const handleSelectAgentSession = useCallback((sessionId: string) => {
    selectSession(sessionId);
    if (!location.pathname.startsWith("/playground")) {
      navigate("/playground");
    }
  }, [location.pathname, navigate, selectSession]);

  const outletContext = useMemo<AdminLayoutContext>(
    () => ({ setHeaderActions, refreshWorkProjects }),
    [refreshWorkProjects, setHeaderActions],
  );

  const handleSignOut = () => {
    signOut();
    navigate("/login", { replace: true });
  };

  const isAdmin = user?.role === "admin";
  const visibleNavItems = navItems.filter((item) => !item.adminOnly || isAdmin);
  const activeItem = visibleNavItems.find((item) => location.pathname.startsWith(item.path));
  const contentMode = location.pathname.startsWith("/playground") ? "fixed" : "scroll";

  return (
    <div className="admin-shell">
      <aside className="admin-sidebar">
        <div className="brand-lockup">
          <img className="brand-logo" src={daybreakLogo} alt="" />
          <div>
            <div className="brand-name">{UI_TEXT.brand}</div>
            <div className="brand-kicker">{UI_TEXT.brandSubtitle}</div>
          </div>
        </div>

        <div className="admin-sidebar-body">
          <div className="admin-sidebar-top">
            <NavLink
              to="/playground"
              className="admin-nav-link"
              onFocus={() => preloadAdminRoute("/playground")}
              onPointerDown={() => preloadAdminRoute("/playground")}
              onPointerEnter={() => preloadAdminRoute("/playground")}
            >
              <MessageSquareCode size={18} />
              <span>{UI_TEXT.navPlayground}</span>
            </NavLink>
            <div className="admin-sidebar-secondary">
              <SessionList
                sessions={sessions}
                loading={sessionsLoading}
                activeSessionId={activeSessionId}
                projectListVersion={projectListVersion}
                onSelect={handleSelectAgentSession}
                onDelete={deleteSession}
                onRefreshSessions={refreshSessions}
                onDropRuntime={dropSessionRuntime}
                onSyncSessionSummaries={syncSessionSummaries}
              />
            </div>
          </div>

          <nav className="admin-nav admin-nav-bottom" aria-label="主导航">
            {visibleNavItems.slice(1).map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className="admin-nav-link"
                  onFocus={() => preloadAdminRoute(item.path)}
                  onPointerDown={() => preloadAdminRoute(item.path)}
                  onPointerEnter={() => preloadAdminRoute(item.path)}
                >
                  <Icon size={18} />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </nav>
        </div>
      </aside>

      <div className="admin-main">
        <header className="admin-topbar">
          <div>
            <div className="page-eyebrow">{activeItem?.eyebrow || "运维管理"}</div>
            <h1>{activeItem?.label || UI_TEXT.console}</h1>
          </div>
          <div className="topbar-actions">
            {headerActions ? <div className="topbar-resource-actions">{headerActions}</div> : null}
            <div className="topbar-session-actions">
              <Avatar size="small" color="red">{user?.username?.[0]?.toUpperCase() || "U"}</Avatar>
              <Button icon={<LogOut size={16} />} theme="borderless" type="tertiary" onClick={handleSignOut} aria-label="退出登录" />
            </div>
          </div>
        </header>
        <main className="admin-content">
          <div className={cx("admin-content-viewport", `admin-content-viewport-${contentMode}`)}>
            <div className={cx("admin-route", `admin-route-${contentMode}`)}>
              <Suspense fallback={<AdminRouteFallback />}>
                <Outlet context={outletContext} />
              </Suspense>
            </div>
          </div>
        </main>
      </div>
    </div>
  );
}

function AdminRouteFallback() {
  return (
    <div className="admin-route-fallback">
      <div className="route-fallback-spinner" />
    </div>
  );
}
