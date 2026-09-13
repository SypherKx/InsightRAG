import React from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { Copy, Check, Terminal } from "lucide-react";

interface FormattedMarkdownProps {
  content: string;
  onCitationClick?: (pageOrIndex: number | string) => void;
}

export const FormattedMarkdown: React.FC<FormattedMarkdownProps> = ({
  content,
  onCitationClick,
}) => {
  const [copiedCode, setCopiedCode] = React.useState<string | null>(null);

  const handleCopy = (code: string) => {
    navigator.clipboard.writeText(code);
    setCopiedCode(code);
    setTimeout(() => setCopiedCode(null), 2000);
  };

  // Helper to render text with interactive citation badges [1], [2], etc.
  const renderTextWithCitations = (text: string) => {
    const parts = text.split(/(\[\d+\])/g);
    if (parts.length === 1) return text;

    return parts.map((part, i) => {
      const match = part.match(/^\[(\d+)\]$/);
      if (match) {
        const citationNum = match[1];
        return (
          <button
            key={i}
            type="button"
            onClick={() => onCitationClick && onCitationClick(Number(citationNum))}
            className="inline-flex items-center justify-center align-baseline mx-0.5 px-1.5 py-0.2 rounded-md bg-purple-100 hover:bg-purple-200 text-purple-900 border border-purple-300 font-mono text-[10px] font-black cursor-pointer shadow-[1px_1px_0px_#000] hover:scale-105 transition-all"
            title={`Source Citation [${citationNum}]`}
          >
            [{citationNum}]
          </button>
        );
      }
      return part;
    });
  };

  return (
    <div className="formatted-markdown-container text-xs sm:text-sm text-gray-900 leading-relaxed space-y-2">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => (
            <h1 className="text-base sm:text-lg font-black text-black border-b-2 border-black pb-1.5 mt-4 mb-2 tracking-tight flex items-center gap-2">
              <span className="w-2 h-4 bg-black rounded-xs inline-block" />
              {children}
            </h1>
          ),
          h2: ({ children }) => (
            <h2 className="text-sm sm:text-base font-black text-gray-950 border-b-2 border-black/15 pb-1 mt-4 mb-2 flex items-center gap-2">
              <span className="w-1.5 h-3 bg-purple-600 rounded-xs inline-block" />
              {children}
            </h2>
          ),
          h3: ({ children }) => (
            <h3 className="text-xs sm:text-sm font-extrabold text-gray-900 mt-3 mb-1.5 flex items-center gap-1.5">
              <span className="w-1.5 h-1.5 bg-black rounded-full inline-block" />
              {children}
            </h3>
          ),
          h4: ({ children }) => (
            <h4 className="text-[11px] sm:text-xs font-black text-purple-800 uppercase tracking-wider mt-2 mb-1">
              {children}
            </h4>
          ),
          p: ({ children }) => {
            if (typeof children === "string") {
              return <p className="my-1.5 leading-relaxed text-gray-800">{renderTextWithCitations(children)}</p>;
            }
            if (Array.isArray(children)) {
              return (
                <p className="my-1.5 leading-relaxed text-gray-800">
                  {children.map((child, idx) =>
                    typeof child === "string" ? (
                      <React.Fragment key={idx}>{renderTextWithCitations(child)}</React.Fragment>
                    ) : (
                      child
                    )
                  )}
                </p>
              );
            }
            return <p className="my-1.5 leading-relaxed text-gray-800">{children}</p>;
          },
          strong: ({ children }) => (
            <strong className="font-extrabold text-gray-950">{children}</strong>
          ),
          em: ({ children }) => (
            <em className="italic text-gray-700">{children}</em>
          ),
          ul: ({ children }) => (
            <ul className="my-2 pl-4 space-y-1.5 list-disc marker:text-black marker:font-bold text-gray-800">
              {children}
            </ul>
          ),
          ol: ({ children }) => (
            <ol className="my-2 pl-4 space-y-1.5 list-decimal marker:text-black marker:font-mono marker:font-bold text-gray-800">
              {children}
            </ol>
          ),
          li: ({ children }) => {
            if (typeof children === "string") {
              return <li className="leading-relaxed pl-0.5">{renderTextWithCitations(children)}</li>;
            }
            if (Array.isArray(children)) {
              return (
                <li className="leading-relaxed pl-0.5">
                  {children.map((child, idx) =>
                    typeof child === "string" ? (
                      <React.Fragment key={idx}>{renderTextWithCitations(child)}</React.Fragment>
                    ) : (
                      child
                    )
                  )}
                </li>
              );
            }
            return <li className="leading-relaxed pl-0.5">{children}</li>;
          },
          blockquote: ({ children }) => (
            <blockquote className="my-2.5 border-l-4 border-black bg-purple-50/60 p-2.5 rounded-r-lg font-medium text-gray-800 border-2 border-black/10 shadow-[2px_2px_0px_#000]">
              {children}
            </blockquote>
          ),
          table: ({ children }) => (
            <div className="my-3 overflow-x-auto rounded-lg border-2 border-black shadow-[3px_3px_0px_#000]">
              <table className="w-full text-left text-xs border-collapse bg-white">{children}</table>
            </div>
          ),
          thead: ({ children }) => (
            <thead className="bg-black text-white font-mono text-[11px] uppercase tracking-wider">{children}</thead>
          ),
          tbody: ({ children }) => (
            <tbody className="divide-y divide-gray-200 font-sans">{children}</tbody>
          ),
          tr: ({ children }) => (
            <tr className="hover:bg-yellow-50/60 transition-colors">{children}</tr>
          ),
          th: ({ children }) => (
            <th className="px-3 py-2 border-r border-gray-800 last:border-r-0 font-bold">{children}</th>
          ),
          td: ({ children }) => (
            <td className="px-3 py-2 border-r border-gray-200 last:border-r-0 text-gray-800 font-medium">
              {children}
            </td>
          ),
          code: ({ node, inline, className, children, ...props }: any) => {
            const codeString = String(children).replace(/\n$/, "");
            if (inline) {
              return (
                <code
                  className="px-1.5 py-0.5 rounded bg-gray-100 border border-gray-300 font-mono text-[11px] text-pink-700 font-bold"
                  {...props}
                >
                  {children}
                </code>
              );
            }
            return (
              <div className="my-3 rounded-lg border-2 border-black overflow-hidden shadow-[3px_3px_0px_#000] bg-zinc-900 text-zinc-100">
                <div className="flex items-center justify-between px-3 py-1.5 bg-black border-b border-zinc-800 text-[10px] font-mono text-zinc-400">
                  <span className="flex items-center gap-1.5 font-bold text-zinc-300">
                    <Terminal className="w-3 h-3 text-[#38bdf8]" />
                    CODE
                  </span>
                  <button
                    type="button"
                    onClick={() => handleCopy(codeString)}
                    className="flex items-center gap-1 px-1.5 py-0.5 rounded bg-zinc-800 hover:bg-zinc-700 text-zinc-300 hover:text-white transition cursor-pointer"
                  >
                    {copiedCode === codeString ? (
                      <>
                        <Check className="w-2.5 h-2.5 text-emerald-400" />
                        <span>Copied</span>
                      </>
                    ) : (
                      <>
                        <Copy className="w-2.5 h-2.5" />
                        <span>Copy</span>
                      </>
                    )}
                  </button>
                </div>
                <pre className="p-3 overflow-x-auto text-[11px] font-mono leading-relaxed">
                  <code>{children}</code>
                </pre>
              </div>
            );
          },
          hr: () => <hr className="my-4 border-t-2 border-black/15" />,
        }}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
};
