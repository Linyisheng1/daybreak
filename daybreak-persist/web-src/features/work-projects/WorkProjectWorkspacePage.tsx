import { Button, Empty, Spin, Toast } from "@douyinfe/semi-ui";
import { ArrowLeft, FileText } from "lucide-react";
import { useMemo, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { ACCESS_TOKEN_HEADER } from "../../shared/api/generated/constants";
import { showApiError } from "../../shared/api/feedback";
import { getStoredAccessToken } from "../../shared/auth/session";
import { UI_TEXT } from "../../shared/lib/uiText";
import { MetricStrip } from "../../shared/components/ResourcePageShell";
import { WorkProjectRecordTabs } from "./ProjectRecordViews";
import { useWorkProjectRecordSnapshot } from "./workProjectRecords";
import { workProjectOwnerNames, WorkProjectStatusTag, WorkProjectTypeTag } from "./workProjectView";

export function WorkProjectWorkspacePage() {
  const params = useParams();
  const navigate = useNavigate();
  const projectId = Number(params.projectId);
  const validProjectId = Number.isFinite(projectId) && projectId > 0 ? projectId : null;
  const { project, records, loading } = useWorkProjectRecordSnapshot(validProjectId);
  const [generating, setGenerating] = useState(false);

  const handleGenerateReport = async () => {
    if (!validProjectId) return;
    setGenerating(true);
    try {
      const token = getStoredAccessToken();
      const resp = await fetch(`/api/work-projects/${validProjectId}/generate-report`, {
        method: "POST",
        headers: { [ACCESS_TOKEN_HEADER]: token || "" },
      });
      if (!resp.ok) throw new Error(UI_TEXT.reportGenerating);
      const blob = await resp.blob();
      const disposition = resp.headers.get("content-disposition") || "";
      const filename = parseContentDispositionFilename(disposition);
      const url = URL.createObjectURL(blob);
      const a = document.createElement("a");
      a.href = url; a.download = filename; a.click();
      URL.revokeObjectURL(url);
      Toast.success({ content: "报告生成成功" });
    } catch (e) {
      showApiError(e);
    } finally {
      setGenerating(false);
    }
  };

  const metrics = useMemo(() => [
    { label: "资产", value: records.assets.length },
    { label: "发现", value: records.findings.length },
    { label: "关系", value: records.graph.edges.length },
    { label: "会话", value: project?.session_count ?? 0 },
  ], [project, records]);

  if (!validProjectId) {
    return <Empty className="empty-state" image={<FileText size={42} />} title="无效项目" description="" />;
  }

  return (
    <section className="work-project-workspace">
      <div className="workspace-back-row">
        <Button icon={<ArrowLeft size={15} />} theme="borderless" type="tertiary" onClick={() => navigate("/work-projects")}>
          返回
        </Button>
      </div>
      <div className="workspace-header">
        {project ? (
          <div className="workspace-title">
            <div className="workspace-title-main">
              <h2>{project.name}</h2>
              {project.description ? <p>{project.description}</p> : null}
              <span>所有者: {workProjectOwnerNames(project)}</span>
            </div>
            <div className="workspace-title-tags">
              <WorkProjectTypeTag project={project} />
              <WorkProjectStatusTag project={project} />
              <Button
                icon={<FileText size={15} />}
                theme="solid"
                type="primary"
                loading={generating}
                onClick={handleGenerateReport}
              >
                {UI_TEXT.generateReport}
              </Button>
            </div>
          </div>
        ) : null}
      </div>

      <MetricStrip metrics={metrics} />

      <Spin spinning={loading}>
        <WorkProjectRecordTabs records={records} className="workspace-tabs" />
      </Spin>
    </section>
  );
}

function parseContentDispositionFilename(disposition: string): string {
  if (!disposition) return "download.docx";
  const utf8 = /filename\*=UTF-8''([^;]+)/i.exec(disposition);
  if (utf8?.[1]) return decodeURIComponent(utf8[1]);
  const quoted = /filename="([^"]+)"/i.exec(disposition);
  if (quoted?.[1]) return quoted[1];
  return "download.docx";
}