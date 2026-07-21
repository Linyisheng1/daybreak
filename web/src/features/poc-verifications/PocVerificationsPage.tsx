import { Button, Empty, Modal, Pagination, Popconfirm, Spin, Tag, Toast, Tooltip } from "@douyinfe/semi-ui";
import {
  Box,
  CheckCircle2,
  FileUp,
  FilterX,
  Play,
  RefreshCcw,
  Search,
  Server,
  ShieldCheck,
  Terminal,
  Trash2,
  Upload,
  XCircle,
} from "lucide-react";
import { ChangeEvent, FormEvent, useCallback, useEffect, useMemo, useState } from "react";
import { useAdminHeaderActions } from "../../app/layouts/AdminLayout";
import { showApiError, showApiSuccess } from "../../shared/api/feedback";
import {
  deletePoc,
  importPoc,
  queryPocRuns,
  queryPocs,
  runPoc,
  type PocDefinition,
  type PocRun,
  type PocRunStatus,
} from "../../shared/api/pocVerifications";
import { queryAvailableSandboxContainers } from "../../shared/api/sandboxContainers";
import type { SandboxContainer } from "../../shared/api/types";
import { ResourceIdentity, ResourceText, RowActions } from "../../shared/components/ResourceCells";
import { MetricStrip } from "../../shared/components/ResourcePageShell";
import { ResourceTable, type ResourceColumn } from "../../shared/components/ResourceTable";
import { formatDateTime } from "../../shared/lib/date";

const DEFAULT_IMPORT = `name: Example HTTP title check
severity: info
category: web
tags:
  - http
description: Verify an authorized target.
command: curl -k -I --max-time 10 "$TARGET"`;

const POC_PAGE_SIZE = 20;
type ExecutionMode = "direct" | "sandbox";

export function PocVerificationsPage() {
  const setHeaderActions = useAdminHeaderActions();
  const [pocs, setPocs] = useState<PocDefinition[]>([]);
  const [runs, setRuns] = useState<PocRun[]>([]);
  const [containers, setContainers] = useState<SandboxContainer[]>([]);
  const [searchInput, setSearchInput] = useState("");
  const [keyword, setKeyword] = useState("");
  const [severity, setSeverity] = useState("");
  const [category, setCategory] = useState("");
  const [page, setPage] = useState(1);
  const [total, setTotal] = useState(0);
  const [selectedPocId, setSelectedPocId] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [running, setRunning] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [importContent, setImportContent] = useState(DEFAULT_IMPORT);
  const [executionMode, setExecutionMode] = useState<ExecutionMode>("direct");
  const [target, setTarget] = useState("");
  const [sandboxContainerId, setSandboxContainerId] = useState<number | "">("");
  const [timeoutSeconds, setTimeoutSeconds] = useState(60);

  const selectedPoc = useMemo(
    () => pocs.find((poc) => poc.id === selectedPocId) ?? pocs[0] ?? null,
    [pocs, selectedPocId],
  );
  const selectedIsNuclei = Boolean(selectedPoc?.raw_content?.id && selectedPoc?.raw_content?.info);
  const selectedSupportsDirect = selectedIsNuclei && !["code", "javascript", "headless", "workflow"]
    .some((protocol) => protocol in (selectedPoc?.raw_content ?? {}));

  const loadAll = useCallback(async () => {
    setLoading(true);
    try {
      const [pocResponse, runResponse, containerResponse] = await Promise.all([
        queryPocs({ page, size: POC_PAGE_SIZE, keyword, severity, category }),
        queryPocRuns({ page: 1, size: 30, poc_id: selectedPocId || undefined }),
        queryAvailableSandboxContainers({ page: 1, size: 100, include_non_running: false }),
      ]);
      const nextPocs = pocResponse.data?.items ?? [];
      setPocs(nextPocs);
      setTotal(pocResponse.data?.total ?? 0);
      setRuns(runResponse.data?.items ?? []);
      setContainers(containerResponse.data?.items ?? []);
      if (!selectedPocId || !nextPocs.some((poc) => poc.id === selectedPocId)) {
        setSelectedPocId(nextPocs[0]?.id ?? null);
      }
    } catch (error) {
      showApiError(error);
    } finally {
      setLoading(false);
    }
  }, [category, keyword, page, selectedPocId, severity]);

  useEffect(() => {
    void loadAll();
  }, [loadAll]);

  useEffect(() => {
    if (selectedPoc && !selectedSupportsDirect) setExecutionMode("sandbox");
  }, [selectedPoc, selectedSupportsDirect]);

  useEffect(() => {
    setHeaderActions(
      <>
        <Tooltip content="刷新">
          <Button icon={<RefreshCcw size={16} />} type="tertiary" loading={loading} onClick={() => void loadAll()} aria-label="刷新" />
        </Tooltip>
        <Button icon={<Upload size={16} />} theme="solid" type="primary" onClick={() => setImportOpen(true)}>
          导入 PoC
        </Button>
      </>,
    );
    return () => setHeaderActions(null);
  }, [loadAll, loading, setHeaderActions]);

  const runSummary = useMemo(() => ({
    matched: runs.filter((run) => run.status === "passed").length,
    clean: runs.filter((run) => run.status === "failed").length,
  }), [runs]);

  const handleSearch = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault();
    setPage(1);
    setKeyword(searchInput.trim());
  };

  const resetFilters = () => {
    setSearchInput("");
    setKeyword("");
    setSeverity("");
    setCategory("");
    setPage(1);
  };

  const handleImport = async () => {
    try {
      const response = await importPoc(importContent);
      showApiSuccess(response);
      setImportOpen(false);
      if (response.data) setSelectedPocId(response.data.id);
      await loadAll();
    } catch (error) {
      showApiError(error);
    }
  };

  const handleFile = async (event: ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    setImportContent(await file.text());
    event.target.value = "";
  };

  const handleRun = async () => {
    if (!selectedPoc) return;
    if (!target.trim()) {
      Toast.warning("请填写目标");
      return;
    }
    if (executionMode === "sandbox" && !sandboxContainerId) {
      Toast.warning("请选择运行中的沙箱");
      return;
    }
    setRunning(true);
    try {
      const response = await runPoc(selectedPoc.id, {
        target: target.trim(),
        execution_mode: executionMode,
        sandbox_container_id: executionMode === "sandbox" ? Number(sandboxContainerId) : null,
        authorized: true,
        authorized_scope: "PoC verification console",
        timeout_seconds: timeoutSeconds,
      });
      showApiSuccess(response);
      await loadAll();
    } catch (error) {
      showApiError(error);
    } finally {
      setRunning(false);
    }
  };

  const handleDelete = async (poc: PocDefinition) => {
    try {
      const response = await deletePoc(poc.id);
      showApiSuccess(response);
      if (selectedPocId === poc.id) setSelectedPocId(null);
      await loadAll();
    } catch (error) {
      showApiError(error);
    }
  };

  const pocColumns: ResourceColumn<PocDefinition>[] = [
    {
      key: "poc",
      header: "模板",
      width: "minmax(300px, 1fr)",
      render: (poc) => (
        <ResourceIdentity
          icon={<ShieldCheck size={18} />}
          title={poc.name}
          detail={templateSummary(poc)}
        />
      ),
    },
    { key: "severity", header: "等级", width: "88px", render: (poc) => <SeverityTag severity={poc.severity} /> },
    { key: "category", header: "协议", width: "100px", render: (poc) => protocolLabel(poc.category) },
    { key: "updated", header: "导入时间", width: "142px", render: (poc) => formatDateTime(poc.updated_at) },
    {
      key: "actions",
      header: "操作",
      width: "92px",
      render: (poc) => (
        <RowActions>
          <Tooltip content="选择验证">
            <Button icon={<Play size={15} />} theme="borderless" type="tertiary" onClick={() => setSelectedPocId(poc.id)} aria-label={`选择 ${poc.name}`} />
          </Tooltip>
          <Popconfirm title="删除 PoC" content={`确认删除 ${poc.name}？`} okType="danger" onConfirm={() => void handleDelete(poc)}>
            <Button icon={<Trash2 size={15} />} theme="borderless" type="danger" aria-label={`删除 ${poc.name}`} />
          </Popconfirm>
        </RowActions>
      ),
    },
  ];

  const runColumns: ResourceColumn<PocRun>[] = [
    { key: "status", header: "结果", width: "88px", render: (run) => <RunStatusTag status={run.status} /> },
    { key: "target", header: "目标", width: "minmax(180px, 1fr)", render: (run) => <ResourceText>{run.target}</ResourceText> },
    { key: "runner", header: "执行器", width: "170px", render: (run) => run.sandbox_container_name },
    { key: "time", header: "耗时", width: "88px", render: (run) => `${run.duration_ms} ms` },
    { key: "updated", header: "时间", width: "150px", render: (run) => formatDateTime(run.finished_at || run.started_at) },
  ];

  return (
    <section className="resource-page poc-page">
      <MetricStrip metrics={[
        { label: "模板总数", value: total },
        { label: "本页模板", value: pocs.length },
        { label: "当前命中", value: runSummary.matched },
        { label: "可用沙箱", value: containers.length },
      ]} />

      <div className="poc-workbench">
        <div className="table-panel poc-library-panel">
          <div className="poc-library-toolbar">
            <form className="poc-search" onSubmit={handleSearch}>
              <Search size={16} />
              <input value={searchInput} onChange={(event) => setSearchInput(event.target.value)} placeholder="搜索名称、模板 ID 或标签" />
              <Button htmlType="submit" theme="solid" type="primary">搜索</Button>
            </form>
            <div className="poc-filters">
              <select value={severity} onChange={(event) => { setSeverity(event.target.value); setPage(1); }} aria-label="风险等级">
                <option value="">全部等级</option>
                <option value="critical">严重</option>
                <option value="high">高危</option>
                <option value="medium">中危</option>
                <option value="low">低危</option>
                <option value="info">信息</option>
                <option value="unknown">未定级</option>
              </select>
              <select value={category} onChange={(event) => { setCategory(event.target.value); setPage(1); }} aria-label="模板协议">
                <option value="">全部协议</option>
                <option value="nuclei-http">HTTP</option>
                <option value="nuclei-requests">Legacy HTTP</option>
                <option value="nuclei-dns">DNS</option>
              </select>
              <Tooltip content="重置筛选">
                <Button icon={<FilterX size={16} />} type="tertiary" onClick={resetFilters} aria-label="重置筛选" />
              </Tooltip>
            </div>
          </div>
          <Spin spinning={loading} wrapperClassName="resource-table-spin">
            {pocs.length === 0 ? (
              <Empty className="empty-state" image={<ShieldCheck size={42} />} title="没有匹配的 PoC" description="" />
            ) : (
              <>
                <ResourceTable<PocDefinition> ariaLabel="PoC library" columns={pocColumns} rows={pocs} rowKey={(poc) => poc.id} />
                <div className="poc-pagination">
                  <span>第 {page} 页，共 {Math.ceil(total / POC_PAGE_SIZE)} 页</span>
                  <Pagination currentPage={page} pageSize={POC_PAGE_SIZE} total={total} onPageChange={setPage} />
                </div>
              </>
            )}
          </Spin>
        </div>

        <aside className="table-panel poc-run-panel">
          <div className="poc-section-heading">
            <div>
              <span>当前模板</span>
              <strong>{selectedPoc?.name || "选择一个 PoC"}</strong>
              {selectedPoc ? <small>{templateSummary(selectedPoc)}</small> : null}
            </div>
            {selectedPoc ? <SeverityTag severity={selectedPoc.severity} /> : null}
          </div>
          {selectedPoc ? (
            <>
              <div className="poc-mode-switch" role="group" aria-label="执行方式">
                <button type="button" className={executionMode === "direct" ? "is-active" : ""} disabled={!selectedSupportsDirect} onClick={() => setExecutionMode("direct")}>
                  <Server size={16} />
                  直接执行
                </button>
                <button type="button" className={executionMode === "sandbox" ? "is-active" : ""} onClick={() => setExecutionMode("sandbox")}>
                  <Box size={16} />
                  沙箱执行
                </button>
              </div>
              <div className="poc-runner-status">
                <Terminal size={15} />
                <span>{executionMode === "direct" ? "Daybreak Nuclei" : "隔离沙箱"}</span>
                <i />
                <span>{executionMode === "direct" ? "无需启动沙箱" : `${containers.length} 个可用`}</span>
              </div>
              <label className="poc-field">
                <span>目标</span>
                <input className="poc-input" value={target} onChange={(event) => setTarget(event.target.value)} placeholder="https://example.com 或 10.0.0.1" />
              </label>
              {executionMode === "sandbox" ? (
                <label className="poc-field">
                  <span>沙箱容器</span>
                  <select className="poc-input" value={sandboxContainerId} onChange={(event) => setSandboxContainerId(event.target.value ? Number(event.target.value) : "")}>
                    <option value="">选择运行中的沙箱</option>
                    {containers.map((container) => (
                      <option key={container.id} value={container.id}>{container.container_name}</option>
                    ))}
                  </select>
                </label>
              ) : null}
              <div className="poc-run-actions">
                <label className="poc-field poc-timeout-row">
                  <span>超时</span>
                  <input className="poc-input" type="number" min={5} max={600} value={timeoutSeconds} onChange={(event) => setTimeoutSeconds(Number(event.target.value) || 60)} />
                </label>
                <Button icon={<Play size={16} />} theme="solid" type="primary" loading={running} onClick={() => void handleRun()}>
                  开始验证
                </Button>
              </div>
              <details className="poc-command-preview">
                <summary>执行命令</summary>
                <pre>{selectedPoc.command}</pre>
              </details>
            </>
          ) : (
            <Empty image={<ShieldCheck size={40} />} title="选择一个 PoC" description="" />
          )}
        </aside>
      </div>

      <div className="table-panel poc-runs-panel">
        <div className="poc-section-heading poc-runs-heading">
          <div>
            <span>验证记录</span>
            <strong>{selectedPoc ? selectedPoc.name : "全部 PoC"}</strong>
          </div>
          <div className="poc-run-counts">
            <span><CheckCircle2 size={15} />命中 {runSummary.matched}</span>
            <span><XCircle size={15} />未命中 {runSummary.clean}</span>
          </div>
        </div>
        {runs.length === 0 ? (
          <Empty className="empty-state" image={<Play size={42} />} title="暂无验证记录" description="" />
        ) : (
          <>
            <ResourceTable<PocRun> ariaLabel="PoC runs" columns={runColumns} rows={runs} rowKey={(run) => run.id} />
            <div className="poc-output-list">
              {runs.slice(0, 3).map((run) => (
                <details key={run.id}>
                  <summary>{run.poc_name} · {run.target}</summary>
                  <pre>{run.error || run.output || "(no output)"}</pre>
                </details>
              ))}
            </div>
          </>
        )}
      </div>

      <Modal title="导入 PoC" visible={importOpen} onCancel={() => setImportOpen(false)} onOk={() => void handleImport()} okText="导入" cancelText="取消" width={760}>
        <div className="poc-import-tools">
          <label className="poc-file-button">
            <FileUp size={16} />
            <span>选择 YAML / JSON 文件</span>
            <input type="file" accept=".yaml,.yml,.json,.txt" onChange={(event) => void handleFile(event)} />
          </label>
        </div>
        <textarea className="poc-import-editor" value={importContent} onChange={(event) => setImportContent(event.target.value)} />
      </Modal>
    </section>
  );
}

function templateSummary(poc: PocDefinition) {
  const id = typeof poc.raw_content.id === "string" ? poc.raw_content.id : `PoC-${poc.id}`;
  const tags = poc.tags.slice(0, 3).join(" · ");
  return tags ? `${id} · ${tags}` : id;
}

function protocolLabel(category: string) {
  if (category === "nuclei-http") return "HTTP";
  if (category === "nuclei-requests") return "Legacy HTTP";
  if (category === "nuclei-dns") return "DNS";
  return category || "Command";
}

function SeverityTag({ severity }: { severity: string }) {
  const normalized = severity.toLowerCase();
  const color = normalized === "critical" || normalized === "high"
    ? "red"
    : normalized === "medium"
      ? "orange"
      : normalized === "low"
        ? "blue"
        : "grey";
  const label = normalized === "critical" ? "严重" : normalized === "high" ? "高危" : normalized === "medium" ? "中危" : normalized === "low" ? "低危" : normalized === "info" ? "信息" : "未定级";
  return <Tag color={color}>{label}</Tag>;
}

function RunStatusTag({ status }: { status: PocRunStatus }) {
  const color = status === "passed" ? "red" : status === "failed" ? "green" : status === "error" ? "orange" : "blue";
  const label = status === "passed" ? "命中" : status === "failed" ? "未命中" : status === "error" ? "异常" : "运行中";
  return <Tag color={color}>{label}</Tag>;
}
