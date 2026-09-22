"use client";

import Image from "next/image";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

import { browserAuthMode, browserSupabaseClient } from "../auth/browser.ts";
import { PublicAuthDrawer } from "./PublicAuthDrawer.tsx";

type AuthMode = "sign-in" | "sign-up";
type ProjectFlow = "new" | "existing";

export function PublicLandingPage() {
  const router = useRouter();
  const authSystem = browserAuthMode();

  const [authOpen, setAuthOpen] = useState(false);
  const [authMode, setAuthMode] = useState<AuthMode>("sign-in");
  const [authenticated, setAuthenticated] = useState(
    authSystem === "development",
  );
  const [authReady, setAuthReady] = useState(authSystem !== "supabase");
  const [pendingFlow, setPendingFlow] = useState<ProjectFlow | null>(null);

  useEffect(() => {
    if (authSystem !== "supabase") {
      return;
    }

    const client = browserSupabaseClient();

    void client.auth.getSession().then(({ data }) => {
      setAuthenticated(data.session !== null);
      setAuthReady(true);
    });

    const { data } = client.auth.onAuthStateChange((_event, session) => {
      setAuthenticated(session !== null);
      setAuthReady(true);
    });

    return () => {
      data.subscription.unsubscribe();
    };
  }, [authSystem]);

  const destinationFor = (flow: ProjectFlow) => `/generation?mode=${flow}`;

  const beginProject = (flow: ProjectFlow) => {
    if (!authReady) {
      return;
    }

    if (authenticated) {
      router.push(destinationFor(flow));
      return;
    }

    setPendingFlow(flow);
    setAuthMode("sign-up");
    setAuthOpen(true);
  };

  const openAuth = (mode: AuthMode) => {
    setPendingFlow(null);
    setAuthMode(mode);
    setAuthOpen(true);
  };

  const finishAuthentication = () => {
    setAuthenticated(true);
    setAuthOpen(false);

    if (pendingFlow) {
      const destination = destinationFor(pendingFlow);
      setPendingFlow(null);
      router.push(destination);
      return;
    }

    router.push("/projects");
  };

  return (
    <>
      <main className="public-home">
        <header className="public-home-header">
          <Link className="public-home-brand" href="/">
            <Image
              src="/vastu-ai-logo.png"
              alt="Vastudraw"
              width={46}
              height={46}
              priority
            />

            <span>
              <strong>Vastudraw</strong>
              <small>AI architectural planning</small>
            </span>
          </Link>

          <div className="public-home-auth-actions">
            {authenticated ? (
              <button
                type="button"
                className="public-home-signup"
                onClick={() => {
                  router.push("/projects");
                }}
              >
                Open workspace
              </button>
            ) : (
              <>
                <button
                  type="button"
                  className="public-home-login"
                  onClick={() => {
                    openAuth("sign-in");
                  }}
                >
                  Log in
                </button>

                <button
                  type="button"
                  className="public-home-signup"
                  onClick={() => {
                    openAuth("sign-up");
                  }}
                >
                  Sign up
                </button>
              </>
            )}
          </div>
        </header>

        <section className="public-home-main">
          <div className="public-home-copy">
            <p className="saas-kicker">Vastudraw studio</p>

            <h1>Start a project</h1>

            <p>
              Generate a new residential plan or analyze an existing plan in the
              same project workflow.
            </p>
          </div>

          <div className="public-home-actions">
            <button
              type="button"
              className="public-home-action-card"
              disabled={!authReady}
              onClick={() => {
                beginProject("new");
              }}
            >
              <span className="public-home-action-icon">+</span>

              <strong>Generate new plan</strong>

              <small>
                Start from plot, orientation, spaces and design intent.
              </small>
            </button>

            <button
              type="button"
              className="public-home-action-card"
              disabled={!authReady}
              onClick={() => {
                beginProject("existing");
              }}
            >
              <span className="public-home-action-icon">↥</span>

              <strong>Analyze my plan</strong>

              <small>
                JPG · PNG · PDF · DXF · DWG → Vastu audit and later
                same-envelope alternatives.
              </small>
            </button>
          </div>
        </section>

        <footer className="public-home-footer">
          <span>© 2026 Vastudraw. All rights reserved.</span>
          <span>Residential planning · Vastu intelligence</span>
        </footer>
      </main>

      <PublicAuthDrawer
        open={authOpen}
        initialMode={authMode}
        onClose={() => {
          setAuthOpen(false);
          setPendingFlow(null);
        }}
        onAuthenticated={finishAuthentication}
      />
    </>
  );
}
