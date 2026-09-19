"use client";

import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useState,
  type ReactNode,
} from "react";

export type Lang = "ko" | "en";

const KEY = "dalba-pw-lang";
/** 기본은 영어. 한국어는 고른 사람에게만 보인다. */
const DEFAULT: Lang = "en";
const Ctx = createContext<{ lang: Lang; setLang: (l: Lang) => void }>({
  lang: DEFAULT,
  setLang: () => {},
});

/**
 * 언어는 화면에서만 바뀐다. 두 언어를 모두 정적 HTML 에 담아 두고 한쪽을 숨긴다.
 * 고른 언어는 브라우저에 남겨 두어 다음에 들어와도 같은 언어로 열린다.
 */
export function LangProvider({ children }: { children: ReactNode }) {
  const [lang, setLangState] = useState<Lang>(DEFAULT);

  useEffect(() => {
    try {
      const saved = localStorage.getItem(KEY);
      if (saved === "en" || saved === "ko") setLangState(saved);
    } catch {
      // 시크릿 창이나 저장소를 막아 둔 브라우저. 기본값으로 둔다.
    }
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang;
  }, [lang]);

  const setLang = useCallback((l: Lang) => {
    setLangState(l);
    try {
      localStorage.setItem(KEY, l);
    } catch {
      // 저장에 실패해도 이번 방문 동안은 바뀐 언어로 보인다.
    }
  }, []);

  return <Ctx.Provider value={{ lang, setLang }}>{children}</Ctx.Provider>;
}

export function useLang() {
  return useContext(Ctx);
}

/** 한국어와 영어를 둘 다 받아 지금 언어에 맞는 쪽을 고른다. */
export function useT() {
  const { lang } = useLang();
  return useCallback(
    <T,>(ko: T, en: T | undefined | null): T => (lang === "en" && en ? en : ko),
    [lang],
  );
}

export function LangSwitch() {
  const { lang, setLang } = useLang();
  return (
    <div className="pw-lang" role="group" aria-label="Language">
      <button
        type="button"
        aria-pressed={lang === "ko"}
        onClick={() => setLang("ko")}
      >
        한국어
      </button>
      <button
        type="button"
        aria-pressed={lang === "en"}
        onClick={() => setLang("en")}
      >
        English
      </button>
    </div>
  );
}
