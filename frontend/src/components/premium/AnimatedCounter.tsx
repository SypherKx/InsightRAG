import { animate, useInView } from "framer-motion";
import { useEffect, useRef } from "react";

export function AnimatedCounter({
  value,
  decimals = 0,
  suffix = "",
  prefix = "",
}: {
  value: number;
  decimals?: number;
  suffix?: string;
  prefix?: string;
}) {
  const ref = useRef<HTMLSpanElement | null>(null);
  const inView = useInView(ref, { once: true, margin: "-10%" });

  useEffect(() => {
    if (!inView) return;
    const controls = animate(0, value, {
      duration: 1.5,
      ease: [0.22, 1, 0.36, 1],
      onUpdate(v) {
        if (ref.current) {
          ref.current.textContent = `${prefix}${v.toLocaleString(undefined, {
            minimumFractionDigits: decimals,
            maximumFractionDigits: decimals,
          })}${suffix}`;
        }
      },
    });
    return () => {
      controls.stop();
    };
  }, [inView, value, prefix, suffix, decimals]);

  return (
    <span ref={ref} className="font-mono tabular-nums">
      {prefix}0{suffix}
    </span>
  );
}
