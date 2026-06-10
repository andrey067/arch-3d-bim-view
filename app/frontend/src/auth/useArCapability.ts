import { useEffect, useState } from 'react';

export function useArCapability(): boolean {
  const [capable, setCapable] = useState(false);
  useEffect(() => {
    const ua = navigator.userAgent || '';
    const isAndroid = /Android/i.test(ua);
    const isIos = /iPhone|iPad|iPod/i.test(ua);
    setCapable(isAndroid || isIos);
  }, []);
  return capable;
}
