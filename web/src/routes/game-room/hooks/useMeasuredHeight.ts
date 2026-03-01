import { useLayoutEffect, useRef, useState } from "react";

export function useMeasuredHeight<T extends HTMLElement>(deps: React.DependencyList) {
  const ref = useRef<T | null>(null);
  const [height, setHeight] = useState(0);

  useLayoutEffect(() => {
    const el = ref.current;
    if (!el) return;

    const update = () => {
      setHeight(el.getBoundingClientRect().height);
    };
    update();

    const ro = new ResizeObserver(update);
    ro.observe(el);
    return () => ro.disconnect();
  }, deps);

  return { ref, height };
}
