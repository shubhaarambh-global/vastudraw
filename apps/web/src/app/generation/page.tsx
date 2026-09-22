import { Phase26CGenerationPage } from "../../components/generation/Phase26CGenerationPage.tsx";

type GenerationPageProps = {
  readonly searchParams: Promise<{
    readonly mode?: string | string[];
  }>;
};

export default async function GenerationPage({
  searchParams,
}: GenerationPageProps) {
  const params = await searchParams;

  const rawMode = Array.isArray(params.mode) ? params.mode[0] : params.mode;

  const initialMode =
    rawMode === "new" || rawMode === "existing" ? rawMode : "choose";

  return <Phase26CGenerationPage initialMode={initialMode} />;
}
