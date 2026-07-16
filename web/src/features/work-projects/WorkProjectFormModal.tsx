import { Button, Input, InputNumber, Select, Spin, Tag, TextArea } from "@douyinfe/semi-ui";
import { FileArchive, FolderKanban, Plus, ScanSearch, Server, Trash2, Upload, UserRound } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import {
  WORK_PROJECT_ASSET_ORIGIN,
  getWorkProjectAssetTypes,
  getWorkProjectTypes,
  isWorkProjectAssetType,
  isWorkProjectType,
  WORK_PROJECT_ASSET_TYPE,
} from "../../shared/api/contract";
import { queryAvailableSandboxContainers, uploadContainerFiles } from "../../shared/api/sandboxContainers";
import { showApiError } from "../../shared/api/feedback";
import { querySystemUsers } from "../../shared/api/systemUsers";
import type {
  CreateWorkProjectRequest,
  SandboxContainer,
  SystemUser,
  WorkProject,
  WorkProjectAssetRequest,
} from "../../shared/api/types";
import { ResourceModal } from "../../shared/components/ResourceModal";
import { useOptionList } from "../../shared/hooks/useOptionList";
import {
  SANDBOX_CONTAINER_STATUS_COLOR,
  SANDBOX_CONTAINER_STATUS_LABEL,
  SYSTEM_USER_ROLE_COLOR,
  SYSTEM_USER_ROLE_LABEL,
  WORK_PROJECT_ASSET_TYPE_LABEL,
  WORK_PROJECT_TYPE_LABEL,
} from "../../shared/lib/labels";

type WorkProjectFormModalProps = {
  open: boolean;
  saving: boolean;
  project?: WorkProject | null;
  onCancel: () => void;
  onSubmit: (payload: CreateWorkProjectRequest) => Promise<void>;
};

type SelectedOption = {
  value?: SystemUser["id"];
};

type AssetFormRow = WorkProjectAssetRequest & {
  existingId?: number;
};

type WorkProjectFormValues = Omit<CreateWorkProjectRequest, "assets"> & {
  assets: AssetFormRow[];
};

const projectTypes = getWorkProjectTypes();
const assetTypes = getWorkProjectAssetTypes();

const EMPTY_ASSET: AssetFormRow = {
  type: assetTypes[0],
  path: "",
  host: "",
  port: null,
};

const EMPTY: WorkProjectFormValues = {
  name: "",
  description: "",
  owner_user_ids: [],
  sandbox_container_id: null,
  assets: [{ ...EMPTY_ASSET }],
  type: projectTypes[0],
};

export function WorkProjectFormModal({ open, saving, project, onCancel, onSubmit }: WorkProjectFormModalProps) {
  const [values, setValues] = useState<WorkProjectFormValues>(EMPTY);
  const [sourceUploading, setSourceUploading] = useState(false);
  const [sourceUploadProgress, setSourceUploadProgress] = useState<number | null>(null);
  const sourceFileInputRef = useRef<HTMLInputElement>(null);
  const loadProjectSandboxContainers = useCallback((params: { page: number; size: number; keyword: string }) => (
    queryAvailableSandboxContainers({
      ...params,
      work_project_id: project?.id,
    })
  ), [project?.id]);
  const { items: sandboxContainers, loading: sandboxLoading } = useOptionList<SandboxContainer>({
    enabled: open,
    query: loadProjectSandboxContainers,
  });
  const { items: users, loading: usersLoading } = useOptionList<SystemUser>({
    enabled: open,
    query: querySystemUsers,
  });
  const editing = Boolean(project);

  useEffect(() => {
    if (!open) return;
    setSourceUploading(false);
    setSourceUploadProgress(null);
    setValues(project ? {
      name: project.name,
      description: project.description,
      owner_user_ids: project.owner_user_ids,
      sandbox_container_id: project.sandbox_container_id ?? null,
      assets: scopeAssetsFromProject(project),
      type: project.type,
    } : { ...EMPTY, assets: [{ ...EMPTY_ASSET }] });
  }, [open, project]);

  const userOptionList = useMemo(() => users.map((user) => ({
    label: <UserOption user={user} />,
    value: user.id,
  })), [users]);

  const sandboxOptionList = useMemo(() => sandboxContainers.map((container) => ({
    label: <SandboxContainerOption container={container} />,
    value: container.id,
  })), [sandboxContainers]);
  const canSubmit = Boolean(values.name.trim()) && values.assets.length > 0
    && values.assets.every(isAssetComplete) && !sourceUploading;
  const sourceAsset = values.assets.find((asset) => asset.type === WORK_PROJECT_ASSET_TYPE.BINARY);

  const selectProjectType = (type: WorkProjectFormValues["type"]) => {
    setValues((current) => ({
      ...current,
      type,
      assets: type === "source_code_audit"
        ? [{ ...EMPTY_ASSET, type: WORK_PROJECT_ASSET_TYPE.BINARY }]
        : [{ ...EMPTY_ASSET }],
    }));
    setSourceUploadProgress(null);
  };

  const uploadSourceFile = async (file: File) => {
    const sandboxContainerId = values.sandbox_container_id;
    if (typeof sandboxContainerId !== "number") {
      showApiError(new Error("请先选择沙箱容器"));
      return;
    }
    setSourceUploading(true);
    setSourceUploadProgress(0);
    try {
      const response = await uploadContainerFiles(
        sandboxContainerId,
        "/data/target",
        [file],
        true,
        (progress) => setSourceUploadProgress(progress.percent),
      );
      const uploaded = response.data?.files[0];
      if (!uploaded) throw new Error("源码文件上传成功，但未返回文件路径");
      setValues((current) => ({
        ...current,
        name: current.name.trim() || sourceProjectName(file.name),
        assets: [{
          type: WORK_PROJECT_ASSET_TYPE.BINARY,
          path: uploaded.path,
          host: "",
          port: null,
        }],
      }));
      setSourceUploadProgress(100);
    } catch (error) {
      setSourceUploadProgress(null);
      showApiError(error);
    } finally {
      setSourceUploading(false);
      if (sourceFileInputRef.current) sourceFileInputRef.current.value = "";
    }
  };

  const updateAsset = (index: number, patch: Partial<AssetFormRow>) => {
    setValues((current) => ({
      ...current,
      assets: current.assets.map((asset, assetIndex) => (
        assetIndex === index ? { ...asset, ...patch } : asset
      )),
    }));
  };

  const removeAsset = (index: number) => {
    setValues((current) => ({
      ...current,
      assets: current.assets.filter((_, assetIndex) => assetIndex !== index),
    }));
  };

  const submit = () => onSubmit({
    ...values,
    name: values.name.trim(),
    description: values.description.trim(),
    assets: values.assets.map(normalizeAsset).filter(isAssetComplete),
  });

  return (
    <ResourceModal
      open={open}
      title={editing ? "编辑项目" : "创建项目"}
      saving={saving}
      submitLabel={editing ? "保存" : "创建"}
      submitDisabled={!canSubmit}
      width={980}
      onCancel={onCancel}
      onSubmit={submit}
    >
      <div className="project-form-grid">
        <label>
          <span>名称</span>
          <Input prefix={<FolderKanban size={16} />} value={values.name} maxLength={255} required
            onChange={(name) => setValues((v) => ({ ...v, name }))}
          />
        </label>
        <label>
          <span>类型</span>
          <Select prefix={<ScanSearch size={16} />} value={values.type}
            onChange={(type) => isWorkProjectType(type) && selectProjectType(type)}
            optionList={projectTypes.map((type) => ({ label: WORK_PROJECT_TYPE_LABEL[type], value: type }))}
          />
        </label>
        <label>
          <span>所有者</span>
          <Select
            prefix={<UserRound size={16} />}
            value={values.owner_user_ids}
            optionList={userOptionList}
            placeholder={usersLoading ? "加载用户中..." : "选择项目所有者"}
            emptyContent={usersLoading ? <Spin size="small" /> : "无用户"}
            loading={usersLoading}
            multiple
            renderSelectedItem={(option: SelectedOption) => ({
              isRenderInTag: true,
              content: users.find((user) => user.id === option.value)?.username ?? String(option.value ?? ""),
            })}
            showClear
            onClear={() => setValues((v) => ({ ...v, owner_user_ids: [] }))}
            onChange={(value) => setValues((v) => ({
              ...v,
              owner_user_ids: Array.isArray(value) ? value.filter((item): item is number => typeof item === "number") : [],
            }))}
          />
        </label>
        <label>
          <span>沙箱容器</span>
          <Select
            prefix={<Server size={16} />}
            value={values.sandbox_container_id ?? undefined}
            optionList={sandboxOptionList}
            placeholder={sandboxLoading ? "加载沙箱容器中..." : "选择沙箱容器"}
            emptyContent={sandboxLoading ? <Spin size="small" /> : "无运行中容器"}
            loading={sandboxLoading}
            showClear
            renderSelectedItem={(option: { value?: number }) => (
              sandboxContainers.find((container) => container.id === option.value)?.container_name ?? String(option.value ?? "")
            )}
            onClear={() => setValues((v) => ({ ...v, sandbox_container_id: null }))}
            onChange={(value) => setValues((v) => ({
              ...v,
              sandbox_container_id: typeof value === "number" ? value : null,
            }))}
          />
        </label>
      </div>

      <label>
        <span>描述</span>
        <TextArea value={values.description} maxLength={2000} autosize={{ minRows: 3, maxRows: 6 }}
          onChange={(description) => setValues((v) => ({ ...v, description }))}
        />
      </label>

      {values.type === "source_code_audit" ? (
        <section className="project-source-upload">
          <header>
            <span>源码文件</span>
            {sourceAsset?.path ? <small title={sourceAsset.path}>{sourceAsset.path}</small> : null}
          </header>
          <input
            ref={sourceFileInputRef}
            type="file"
            hidden
            accept=".zip,.7z,.tar,.gz,.tgz,.bz2,.xz"
            onChange={(event) => {
              const file = event.currentTarget.files?.[0];
              if (file) void uploadSourceFile(file);
            }}
          />
          <div className="project-source-upload-action">
            <Button
              icon={sourceAsset?.path ? <FileArchive size={16} /> : <Upload size={16} />}
              loading={sourceUploading}
              disabled={values.sandbox_container_id === null}
              onClick={() => sourceFileInputRef.current?.click()}
            >
              {sourceAsset?.path ? "重新选择源码文件" : "选择源码文件上传"}
            </Button>
            {sourceUploadProgress !== null ? (
              <span>{sourceUploadProgress < 100 ? `上传中 ${sourceUploadProgress}%` : "上传完成"}</span>
            ) : null}
          </div>
        </section>
      ) : <section className="project-assets-editor">
        <header>
          <span>资产</span>
          <Button
            icon={<Plus size={14} />}
            size="small"
            theme="borderless"
            type="tertiary"
            onClick={() => setValues((v) => ({ ...v, assets: [...v.assets, { ...EMPTY_ASSET }] }))}
          >
            添加资产
          </Button>
        </header>
        <div className="project-assets-rows">
          {values.assets.map((asset, index) => (
            <article key={index} className="project-asset-row">
              <label>
                <span>类型</span>
                <Select
                  value={asset.type}
                  disabled={Boolean(asset.existingId)}
                  optionList={assetTypes.map((type) => ({ label: WORK_PROJECT_ASSET_TYPE_LABEL[type], value: type }))}
                  onChange={(type) => isWorkProjectAssetType(type) && updateAsset(index, resetAssetForType(type))}
                />
              </label>
              {asset.type === WORK_PROJECT_ASSET_TYPE.BINARY ? (
                <label>
                  <span>路径</span>
                  <Input
                    value={asset.path}
                    maxLength={500}
                    required
                    onChange={(path) => updateAsset(index, { path })}
                  />
                </label>
              ) : (
                <>
                  <label>
                    <span>{ASSET_HOST_FIELD_LABEL[asset.type]}</span>
                    <Input value={asset.host} maxLength={255} onChange={(host) => updateAsset(index, { host })} />
                  </label>
                  {asset.type === WORK_PROJECT_ASSET_TYPE.SERVICE ? (
                    <label>
                      <span>端口</span>
                      <InputNumber value={asset.port ?? undefined} min={1} max={65535} onChange={(port) => updateAsset(index, { port: typeof port === "number" ? port : null })} />
                    </label>
                  ) : null}
                </>
              )}
              <Button
                icon={<Trash2 size={14} />}
                theme="borderless"
                type="danger"
                disabled={values.assets.length <= 1}
                aria-label="移除资产"
                onClick={() => removeAsset(index)}
              />
            </article>
          ))}
        </div>
      </section>}
    </ResourceModal>
  );
}

function sourceProjectName(filename: string) {
  return filename.replace(/\.(?:tar\.gz|tar\.bz2|tar\.xz|zip|7z|tar|tgz|gz|bz2|xz)$/i, "");
}

function UserOption({ user }: { user: SystemUser }) {
  return (
    <div className="project-user-option">
      <span>{user.username}</span>
      <small>{user.email || "无邮箱"}</small>
      <Tag color={SYSTEM_USER_ROLE_COLOR[user.role]}>{SYSTEM_USER_ROLE_LABEL[user.role]}</Tag>
    </div>
  );
}

function SandboxContainerOption({ container }: { container: SandboxContainer }) {
  return (
    <div className="project-sandbox-option">
      <span>{container.container_name}</span>
      <small>ID: {container.id} · {container.container_hash || "等待哈希"}</small>
      <Tag color={SANDBOX_CONTAINER_STATUS_COLOR[container.status]}>
        {SANDBOX_CONTAINER_STATUS_LABEL[container.status]}
      </Tag>
    </div>
  );
}

function assetFromProject(asset: WorkProject["assets"][number]): AssetFormRow {
  return {
    existingId: asset.id,
    type: asset.type,
    path: asset.path,
    host: asset.host,
    port: asset.port,
  };
}

function scopeAssetsFromProject(project: WorkProject): AssetFormRow[] {
  const assets = project.assets
    .filter((asset) => asset.origin === WORK_PROJECT_ASSET_ORIGIN.SCOPE)
    .map(assetFromProject);
  return assets.length ? assets : [{ ...EMPTY_ASSET }];
}

function normalizeAsset(asset: AssetFormRow): WorkProjectAssetRequest {
  if (asset.type === WORK_PROJECT_ASSET_TYPE.BINARY) {
    return { type: asset.type, path: asset.path.trim(), host: "", port: null };
  }
  return {
    type: asset.type,
    path: "",
    host: asset.host.trim(),
    port: asset.type === WORK_PROJECT_ASSET_TYPE.SERVICE ? asset.port : null,
  };
}

function isAssetComplete(asset: WorkProjectAssetRequest): boolean {
  if (asset.type === WORK_PROJECT_ASSET_TYPE.BINARY) return Boolean(asset.path.trim());
  return Boolean(asset.host.trim());
}

function resetAssetForType(type: WorkProjectAssetRequest["type"]): Partial<AssetFormRow> {
  return { type, path: "", host: "", port: null };
}

// Label for the `host` input field, which carries a different identifier per asset type.
const ASSET_HOST_FIELD_LABEL: Record<Exclude<WorkProjectAssetRequest["type"], typeof WORK_PROJECT_ASSET_TYPE.BINARY>, string> = {
  [WORK_PROJECT_ASSET_TYPE.SERVICE]: "主机",
  [WORK_PROJECT_ASSET_TYPE.DOMAIN]: "域名",
  [WORK_PROJECT_ASSET_TYPE.NETWORK]: "网络 (CIDR)",
};
