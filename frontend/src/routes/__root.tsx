import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import {
  Outlet,
  Link,
  createRootRouteWithContext,
  useRouter,
  HeadContent,
  Scripts,
} from "@tanstack/react-router";

import appCss from "../styles.css?url";

function NotFoundComponent() {
  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--canvas)] text-[var(--ink)] px-4">
      <div className="max-w-md text-center">
        <h1 className="text-3xl font-serif font-normal text-[var(--ink)]">Page not found</h1>
        <p className="mt-2 text-sm text-[var(--muted)]">
          The requested page does not exist in our RAG workspace.
        </p>
        <div className="mt-6">
          <Link to="/">
            <button className="button-primary">Return to home</button>
          </Link>
        </div>
      </div>
    </div>
  );
}

function ErrorComponent({ error, reset }: { error: Error; reset: () => void }) {
  console.error(error);
  const router = useRouter();

  return (
    <div className="flex min-h-screen items-center justify-center bg-[var(--canvas)] text-[var(--ink)] px-4">
      <div className="max-w-md text-center">
        <h1 className="text-2xl font-serif font-normal text-[var(--ink)]">
          An error occurred
        </h1>
        <p className="mt-2 text-sm text-[var(--muted)]">
          Something went wrong while rendering the view.
        </p>
        <div className="mt-6 flex flex-wrap justify-center gap-3">
          <button
            onClick={() => {
              router.invalidate();
              reset();
            }}
            className="button-primary"
          >
            Try again
          </button>
          <a href="/" className="button-secondary">
            Go home
          </a>
        </div>
      </div>
    </div>
  );
}

export const Route = createRootRouteWithContext<{ queryClient: QueryClient }>()({
  head: () => ({
    meta: [
      { charSet: "utf-8" },
      { name: "viewport", content: "width=device-width, initial-scale=1" },
      { title: "InsightRAG AI — Retrieval-Augmented Generation for Healthcare & Education" },
      {
        name: "description",
        content:
          "AI-powered healthcare and educational intelligence platform that detects clinical vitals anomalies, uncovers protocol root causes, and delivers grounded, context-aware explanations using a local Retrieval-Augmented Generation (RAG) pipeline and semantic vector search.",
      },
      { name: "author", content: "InsightRAG AI" },
      { property: "og:title", content: "InsightRAG AI — Healthcare & Education RAG" },
      { property: "og:description", content: "Warm cream canvas, coral accents, serif display headlines, and dark navy product chrome." },
      { property: "og:type", content: "website" },
    ],
    links: [
      {
        rel: "stylesheet",
        href: appCss,
      },
      {
        rel: "preconnect",
        href: "https://fonts.googleapis.com",
      },
      {
        rel: "preconnect",
        href: "https://fonts.gstatic.com",
        crossOrigin: "anonymous",
      },
      {
        rel: "stylesheet",
        href: "https://fonts.googleapis.com/css2?family=Cormorant+Garamond:ital,wght@0,400;0,500;0,600;0,700;1,400&family=Inter:wght@400;500;600;700&family=JetBrains+Mono:wght@400;500;600&display=swap",
      },
    ],
  }),
  shellComponent: RootShell,
  component: RootComponent,
  notFoundComponent: NotFoundComponent,
  errorComponent: ErrorComponent,
});

function RootShell({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <head>
        <HeadContent />
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  );
}

function RootComponent() {
  const { queryClient } = Route.useRouteContext();

  return (
    <QueryClientProvider client={queryClient}>
      <Outlet />
    </QueryClientProvider>
  );
}
