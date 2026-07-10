import { Button, Input } from "@douyinfe/semi-ui";
import { Crosshair, KeyRound, Mail } from "lucide-react";
import { FormEvent, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { login } from "../../shared/api/systemUsers";
import { showApiError } from "../../shared/api/feedback";
import { useAuth } from "../../shared/auth/AuthProvider";
import { UI_TEXT } from "../../shared/lib/uiText";
import daybreakLogo from "../../assets/z3r0-logo.png";

type LoginLocationState = {
  from?: { pathname?: string };
};

export function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const { signIn } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const from = (location.state as LoginLocationState | null)?.from?.pathname || "/playground";

  const handleSubmit = async (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setSubmitting(true);
    try {
      const response = await login({ email, password });
      if (response.data?.token) {
        signIn(response.data.token);
        navigate(from, { replace: true });
      }
    } catch (error) {
      showApiError(error);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <main className="login-page">
      <div className="login-grid" aria-hidden="true" />
      <div className="login-scanline" aria-hidden="true" />
      <section className="login-panel" aria-labelledby="login-title">
        <div className="login-brand">
          <img className="brand-logo large" src={daybreakLogo} alt="" />
          <div>
            <span className="login-kicker">{UI_TEXT.brandSubtitle}</span>
            <h1 id="login-title">{UI_TEXT.console}</h1>
          </div>
        </div>

        <form className="login-form" onSubmit={handleSubmit}>
          <label>
            <span>{UI_TEXT.email}</span>
            <Input
              size="large"
              type="email"
              prefix={<Mail size={16} />}
              value={email}
              onChange={setEmail}
              autoComplete="email"
              placeholder="输入邮箱"
              required
            />
          </label>
          <label>
            <span>{UI_TEXT.password}</span>
            <Input
              size="large"
              mode="password"
              prefix={<KeyRound size={16} />}
              value={password}
              onChange={setPassword}
              autoComplete="current-password"
              placeholder="输入密码"
              required
            />
          </label>
          <Button
            htmlType="submit"
            theme="solid"
            type="primary"
            size="large"
            block
            loading={submitting}
            icon={<Crosshair size={17} />}
          >
            {UI_TEXT.signIn}
          </Button>
        </form>
      </section>
    </main>
  );
}
