import { ContainerShellProvider } from "../../features/container-shell/ContainerShellProvider";
import { AgentSessionProvider } from "../../features/playground/AgentSessionProvider";
import { ErrorBoundary } from "../../shared/components/ErrorBoundary";
import { AdminLayout } from "./AdminLayout";

export function ProtectedAdminShell() {
  return (
    <ErrorBoundary>
      <div className="admin-app">
        <AgentSessionProvider>
          <ContainerShellProvider>
            <AdminLayout />
          </ContainerShellProvider>
        </AgentSessionProvider>
      </div>
    </ErrorBoundary>
  );
}
