import { ProjectEditorPage } from "../../components/editor/ProjectEditorPage.tsx";
import { SaasShell } from "../../components/shell/SaasShell.tsx";

interface EditorPageProps {
  readonly searchParams: Promise<{
    readonly project?: string | readonly string[];
  }>;
}

export default async function EditorPage({ searchParams }: EditorPageProps) {
  const params = await searchParams;
  const projectParam = params.project;
  const projectId =
    typeof projectParam === "string"
      ? projectParam
      : (projectParam?.[0] ?? null);

  return (
    <SaasShell
      userLabel="Workspace member"
      contentClassName="saas-content-editor"
    >
      <ProjectEditorPage projectId={projectId} />
    </SaasShell>
  );
}
