# 🎨 InsightRAG — Frontend Architecture & Developer Guide

Modern, responsive Neo-Brutalist Single Page Application (SPA) built with **React 19**, **Vite 7**, **Tailwind CSS v4**, and **TanStack Router**.

---

## 🧭 Directory Map

```
frontend/src/
├── routes/               # 🧭 TanStack File-Based Routing System
│   ├── __root.tsx        # Master shell: HTML head, query client, AuthProvider & modal
│   ├── index.tsx         # Landing page with multi-platform OS switcher & locked installer
│   ├── app.tsx           # Studio Zero-Trust Auth Guard (requires active login)
│   ├── app.upload.tsx    # Multi-file drag-and-drop document ingestion studio
│   ├── app.query.tsx     # Fullscreen RAG chat studio with diagram previews
│   ├── app.dashboard.tsx # Knowledge base document manager & index statistics
│   ├── app.anomalies.tsx # Anomaly detection & statistical metrics explorer
│   ├── app.anomalies.$id.tsx # Deep-dive root-cause attribution breakdown
│   ├── docs.tsx          # Interactive documentation & API reference
│   ├── features.tsx      # System capabilities, benchmarks & feature cards
│   └── about.tsx         # Architecture deep-dive & design philosophy
│
├── components/           # 🧩 Modular Component Library
│   ├── auth/             # 🔐 Auth Components
│   │   ├── index.ts      # Barrel exports
│   │   └── AuthModal.tsx # Neo-Brutalist Google 1-Click + Email/Password popup
│   ├── brand/            # Brand visual assets & logos (BrandLogo.tsx)
│   ├── dashboard/        # Studio layout shells & sidebar navigations
│   ├── marketing/        # Landing page components, navbar & footer
│   ├── premium/          # Ambient lighting, glass cards & glow badges
│   └── ui/               # Accessible Shadcn/UI primitives (buttons, dialogs, tabs)
│
├── lib/                  # 🛠️ Core Utilities & Contexts
│   ├── firebase.ts       # Firebase Web SDK initialization & Google Analytics
│   ├── auth-context.tsx  # User auth lifecycle, login/logout & backend sync
│   └── utils.ts          # ClassName merging (`clsx` + `tailwind-merge`)
│
├── services/             # 📡 API Client
│   └── api.ts            # Axios instance with automatic Firebase Bearer token interceptor
│
└── styles.css            # Tailwind CSS design system tokens, fonts & animations
```

---

## 🔑 Authentication Architecture
- **Provider**: `AuthProvider` in [`lib/auth-context.tsx`](lib/auth-context.tsx) wraps the entire app in `routes/__root.tsx`.
- **Protected Routes**: [`routes/app.tsx`](routes/app.tsx) acts as a **Zero-Trust Guard**. Unauthenticated visitors trying to enter `/app/*` see an "Access Restricted" lock card instead of raw studio features.
- **PowerShell Command Gating**: In [`routes/index.tsx`](routes/index.tsx), the 1-line launch installer is obfuscated with a lock badge until the user signs in with Google or Email.
- **API Token Injection**: [`services/api.ts`](services/api.ts) automatically attaches `Authorization: Bearer <token>` to all requests via an Axios interceptor.

---

## 🛠️ Running Locally (Standalone)

```bash
# From frontend folder:
npm run dev
```
UI will be live at: **`http://localhost:5173`**

