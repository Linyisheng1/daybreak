import type { ReactNode } from "react";
import {
  Activity,
  ArrowRight,
  Bot,
  Boxes,
  Braces,
  ClipboardCheck,
  Code2,
  Database,
  FileCheck2,
  FileSearch,
  FolderKanban,
  GitBranch,
  Layers3,
  LockKeyhole,
  Network,
  Route,
  Server,
  ShieldCheck,
  SquareTerminal,
  Workflow,
  type LucideIcon,
} from "lucide-react";
import { cx } from "../../shared/lib/className";

const repositoryUrl = "https://github.com/Linyisheng1/daybreak";
const docsOverviewUrl = "https://github.com/Linyisheng1/daybreak/blob/main/docs/en/guide/overview.md";
const egressModes = ["Direct", "HTTP", "HTTPS", "SOCKS5"];

type LandingPrimaryAction = {
  label: string;
  href?: string;
  external?: boolean;
  onSelect?: () => void;
};

type LandingContentProps = {
  logoSrc: string;
  primaryAction: LandingPrimaryAction;
};

type CardItem = {
  title: string;
  text: string;
  icon: LucideIcon;
  kicker?: string;
  items?: string[];
};

type AgentItem = {
  code: string;
  name: string;
  role: string;
  detail: string;
  icon: LucideIcon;
};

const planes: CardItem[] = [
  {
    title: "控制层",
    kicker: "FastAPI",
    text: "负责用户、会话、工作项目、受管主机、沙箱镜像、容器、出口代理和系统配置的认证资源管理。",
    icon: Braces,
    items: ["REST 资源", "WebSocket 会话入口", "访问与所有权"],
  },
  {
    title: "运行时层",
    kicker: "Agent sessions",
    text: "协调主导智能体和专家智能体，流式传输规范化事件，保持时间线连续性，并在结果可用时恢复长时间运行的工作。",
    icon: Workflow,
    items: ["会话运行时", "智能体图谱", "可回放时间线"],
  },
  {
    title: "取证层",
    kicker: "WorkProject",
    text: "通过持久化资产、发现、关系图谱边、攻击路径、任务和智能体摘要，将评估状态保持在模型上下文之外。",
    icon: FileCheck2,
    items: ["资产与范围", "发现与图谱", "攻击路径"],
  },
  {
    title: "执行层",
    kicker: "Sandbox pool",
    text: "提供基于Docker的隔离执行环境，包括Shell、文件、noVNC、命令执行、沙箱技能和容器级出站网络策略。",
    icon: SquareTerminal,
    items: ["受管Docker主机", "沙箱控制代理", "统一出口"],
  },
];

const runtimePath: CardItem[] = [
  {
    title: "操作员工作台",
    text: "React控制台整合了对话、项目记录、图谱审查、沙箱选择、终端、文件和noVNC。",
    icon: Layers3,
  },
  {
    title: "控制层",
    text: "FastAPI接收REST和WebSocket流量，解析会话、项目、沙箱和用户边界。",
    icon: Braces,
  },
  {
    title: "会话运行时",
    text: "运行时执行选定的智能体图谱，将提供方输出转换为应用级事件。",
    icon: Bot,
  },
  {
    title: "工具层",
    text: "智能体工作涉及项目记录、知识、委托专家或选定的沙箱资源。",
    icon: Workflow,
  },
  {
    title: "持久化",
    text: "PostgreSQL存储时间线帧、项目取证、资源状态和后台任务状态。",
    icon: Database,
  },
];

const evidenceNodes: CardItem[] = [
  { title: "范围", text: "声明的目标和项目边界", icon: ShieldCheck },
  { title: "资产", text: "服务、域名、网络、二进制文件", icon: Boxes },
  { title: "关系", text: "结构和攻击图谱边", icon: GitBranch },
  { title: "发现", text: "证明、影响、严重性、状态", icon: FileSearch },
  { title: "攻击路径", text: "从访问到影响的有序遍历", icon: Route },
  { title: "审查", text: "记录、图谱视图、时间线回放", icon: ClipboardCheck },
];

const workbenchSurfaces: CardItem[] = [
  { title: "工作台", text: "实时对话、智能体选择、流式状态、子智能体面板和沙箱操作。", icon: Activity },
  { title: "项目运营", text: "项目元数据、所有者、范围资产、会话、记录、图谱和攻击路径。", icon: FolderKanban },
  { title: "主机管理", text: "Docker主机清单，用于跨受管基础设施分发沙箱工作负载。", icon: Server },
  { title: "出口代理", text: "受管HTTP、HTTPS和SOCKS5上游，用于容器级出站路由。", icon: Network },
  { title: "沙箱镜像", text: "可复用的执行基线，定义容器可用的工具和控制代理。", icon: Boxes },
  { title: "沙箱容器", text: "运行时实例，包含所有者、状态、端口、控制代理令牌和出口模式。", icon: SquareTerminal },
];

const agents: AgentItem[] = [
  { code: "cso", name: "破晓", role: "首席安全负责人", detail: "任务分解、团队协调、结果整合。", icon: Workflow },
  { code: "cae", name: "V3ra", role: "代码审计工程师", detail: "源代码审计、依赖审查、修复验证。", icon: ClipboardCheck },
  { code: "cie", name: "L1ly", role: "情报收集工程师", detail: "情报收集、资产发现、关系映射。", icon: FileSearch },
  { code: "cpe", name: "Fr4nk", role: "渗透测试工程师", detail: "渗透测试、漏洞验证、影响确认。", icon: ShieldCheck },
  { code: "cre", name: "J4m3", role: "逆向分析工程师", detail: "逆向分析、固件反汇编、二进制解包。", icon: Code2 },
  { code: "cce", name: "Nu1L", role: "密码学工程师", detail: "密码分析、密钥审查、安全评估。", icon: LockKeyhole },
];

export function LandingContent({ logoSrc, primaryAction }: LandingContentProps) {
  return (
    <main className="landing-page">
      <div className="landing-grid" aria-hidden="true" />
      <div className="landing-scanline" aria-hidden="true" />

      <section className="landing-hero" aria-label="破晓 Daybreak landing page">
        <div className="landing-hero-copy">
          <img className="landing-hero-logo" src={logoSrc} width="1000" height="1000" alt="破晓 Daybreak logo" />
          <span className="page-eyebrow">开源安全评估工作台</span>
          <h1>安全评估工作台</h1>
          <p>面向控制平台的授权渗透测试、漏洞发现、代码审计和安全研究平台。</p>
          <div className="landing-actions">
            <ActionLink action={primaryAction} primary />
            <ActionLink action={{ label: "GitHub", href: repositoryUrl, external: true }} icon={GitBranch} ghost />
          </div>
        </div>
        <ArchitecturePanel />
      </section>

      <Section
        eyebrow="架构层级"
        title="系统将管理、运行时、取证和执行关注点分离。"
        description="每个层级映射到实际应用资源：API路由与服务、会话运行时、工作项目记录、Docker基础设施、沙箱控制代理和PostgreSQL持久化。"
      >
        <div className="landing-card-grid landing-card-grid-4">
          {planes.map((item) => <Card key={item.title} item={item} accent />)}
        </div>
      </Section>

      <Section eyebrow="运行时流程" title="实时交互、后台工作和回放共享一个应用事件模型。">
        <div className="landing-card-grid landing-card-grid-5">
          {runtimePath.map((item, index) => <Card key={item.title} item={item} index={index} arrow={index < runtimePath.length - 1} />)}
        </div>
      </Section>

      <Section
        eyebrow="取证模型"
        title="工作项目将临时调查输出转化为持久的审查材料。"
        description="资产是图节点，关系是有向边，发现携带证明和影响，攻击路径重建访问或影响如何沿图谱推进。"
      >
        <div className="landing-card-grid landing-card-grid-6">
          {evidenceNodes.map((item, index) => <Card key={item.title} item={item} index={index} arrow={index < evidenceNodes.length - 1} />)}
        </div>
      </Section>

      <Section eyebrow="分布式沙箱与出口" title="执行资源作为基础设施进行管理，具有统一的出站策略面。">
        <div className="landing-sandbox-topology">
          <div className="landing-topology-map" aria-label="Sandbox and egress topology">
            <div className="landing-topology-node landing-topology-project">WorkProject / Session</div>
            <div className="landing-topology-hosts">
              {["受管主机 A", "受管主机 B"].map((title) => (
                <div className="landing-topology-node" key={title}>
                  <strong>{title}</strong>
                  <span>Docker 沙箱</span>
                </div>
              ))}
            </div>
            <div className="landing-topology-node"><span>沙箱控制代理</span><strong>shell / files / noVNC / egress API</strong></div>
            <div className="landing-topology-node"><span>容器内出口代理</span><strong>127.0.0.1:8118</strong></div>
            <div className="landing-egress-modes">{egressModes.map((mode) => <span key={mode}>{mode}</span>)}</div>
          </div>
          <div className="landing-panel landing-topology-copy">
            <h3>沙箱是一个受管资源边界，而非附带的命令运行器。</h3>
            <p>操作员和智能体通过选定的运行中容器工作。同一边界支持命令执行、Shell、文件、浏览器/noVNC审查、沙箱技能和容器级网络身份。</p>
            <p>出口策略通过本地代理在容器内应用，可直接路由或通过受管的HTTP、HTTPS和SOCKS5上游路由。</p>
          </div>
        </div>
      </Section>

      <Section eyebrow="操作员工作台" title="前端暴露了与后端控制层相同的资源模型。">
        <div className="landing-card-grid landing-card-grid-3">
          {workbenchSurfaces.map((item) => <Card key={item.title} item={item} />)}
        </div>
      </Section>

      <Section eyebrow="专家团队" title="专家角色反映了专业安全评估中的分工。">
        <div className="landing-card-grid landing-card-grid-3">
          {agents.map((agent) => <AgentCard key={agent.code} agent={agent} />)}
        </div>
      </Section>

      <Section className="landing-security" eyebrow="运营边界" title="仅限授权使用。">
        <div className="landing-panel landing-boundary">
          <p>破晓仅用于合法的、明确授权的安全测试、风险评估、代码审计和研究。它不授权测试、扫描、访问或影响任何第三方系统、网络、服务、账户或数据。</p>
          <a className="landing-inline-link" href={docsOverviewUrl} target="_blank" rel="noopener noreferrer">
            阅读文档
            <ArrowRight size={16} />
          </a>
        </div>
      </Section>
    </main>
  );
}

function Section({
  children,
  className = "",
  description,
  eyebrow,
  title,
}: {
  children: ReactNode;
  className?: string;
  description?: string;
  eyebrow: string;
  title: string;
}) {
  return (
    <section className={cx("landing-section", className)}>
      <div className="landing-section-heading">
        <span className="page-eyebrow">{eyebrow}</span>
        <h2>{title}</h2>
        {description ? <p>{description}</p> : null}
      </div>
      {children}
    </section>
  );
}

function ArchitecturePanel() {
  return (
    <div className="landing-panel landing-architecture-panel" aria-label="破晓 architecture overview">
      <div className="landing-panel-heading">
        <span className="page-eyebrow">系统模型</span>
        <h2>工作台、API、运行时、取证、沙箱、出口和持久化是显式层级。</h2>
      </div>
      <div className="landing-architecture-canvas">
        <div className="landing-diagram-node landing-diagram-wide">授权操作员</div>
        <div className="landing-api-row">
          <div className="landing-diagram-node">React 工作台</div>
          <ArrowRight size={17} />
          <div className="landing-diagram-node">FastAPI 控制层</div>
        </div>
        <div className="landing-plane-row">
          {planes.map(({ icon: Icon, title }) => (
            <div className="landing-diagram-node landing-plane-node" key={title}>
              <Icon size={18} />
              <span>{title}</span>
            </div>
          ))}
        </div>
        <div className="landing-diagram-node landing-diagram-wide">
          <Database size={18} />
          <span>PostgreSQL 持久化</span>
        </div>
      </div>
    </div>
  );
}

function Card({ accent = false, arrow, index, item }: { accent?: boolean; arrow?: boolean; index?: number; item: CardItem }) {
  const Icon = item.icon;
  return (
    <article className={cx("landing-card", accent && "landing-card-accent")}>
      <div className="landing-card-topline">
        <span>{item.kicker ?? (index != null ? String(index + 1).padStart(2, "0") : "")}</span>
        <Icon size={20} />
      </div>
      <h3>{item.title}</h3>
      <p>{item.text}</p>
      {item.items ? <ul>{item.items.map((entry) => <li key={entry}>{entry}</li>)}</ul> : null}
      {arrow ? <ArrowRight className="landing-card-arrow" size={18} aria-hidden="true" /> : null}
    </article>
  );
}

function AgentCard({ agent }: { agent: AgentItem }) {
  const Icon = agent.icon;
  return (
    <article className="landing-card landing-card-agent">
      <div className="landing-card-topline">
        <span>{agent.code}</span>
        <Icon size={18} />
      </div>
      <strong>{agent.name}</strong>
      <h3>{agent.role}</h3>
      <p>{agent.detail}</p>
    </article>
  );
}

function ActionLink({ action, ghost = false, icon: Icon = ShieldCheck, primary = false }: {
  action: LandingPrimaryAction;
  ghost?: boolean;
  icon?: LucideIcon;
  primary?: boolean;
}) {
  const className = cx(
    "landing-action-link",
    primary ? "landing-action-primary" : ghost ? "landing-action-ghost" : "landing-action-secondary",
  );

  const content = (
    <>
      <Icon size={17} />
      <span>{action.label}</span>
    </>
  );

  if (action.href) {
    return (
      <a className={className} href={action.href} target={action.external ? "_blank" : undefined} rel={action.external ? "noopener noreferrer" : undefined}>
        {content}
      </a>
    );
  }

  return <button className={className} type="button" onClick={action.onSelect}>{content}</button>;
}