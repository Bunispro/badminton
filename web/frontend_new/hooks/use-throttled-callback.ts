import { useRef, useCallback } from 'react';

export function useThrottledCallback<T extends (...args: any[]) => void>(
  callback: T,
  delay: number = 200
): (...args: Parameters<T>) => void {
  const lastClickRef = useRef<number>(0);

  return useCallback((...args: Parameters<T>) => {
    const now = Date.now();
    if (now - lastClickRef.current >= delay) {
      lastClickRef.current = now;
      callback(...args);
    }
  }, [callback, delay]);
}
