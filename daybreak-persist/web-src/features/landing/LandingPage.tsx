import { useNavigate } from "react-router-dom";
import daybreakLogo from "../../assets/z3r0-logo.png";
import { useAuth } from "../../shared/auth/AuthProvider";
import { LandingContent } from "./LandingContent";

export function LandingPage() {
  const { isAuthenticated } = useAuth();
  const navigate = useNavigate();
  const consolePath = isAuthenticated ? "/playground" : "/login";

  return <LandingContent logoSrc={daybreakLogo} primaryAction={{ label: "打开工作台", onSelect: () => navigate(consolePath) }} />;
}
