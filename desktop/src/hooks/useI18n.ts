import { useState, useCallback } from "react";
import en from "./i18n.json";

type Lang = "en" | "hi" | "ur";

const translations: Record<Lang, typeof en> = {
  en: en,
  hi: (en as any).hi || en,
  ur: (en as any).ur || en,
};

export function useI18n() {
  const [lang, setLang] = useState<Lang>(() => {
    return (localStorage.getItem("devin-lang") as Lang) || "en";
  });

  const t = useCallback(
    (path: string): string => {
      const keys = path.split(".");
      let val: any = translations[lang] || translations.en;
      for (const key of keys) {
        val = val?.[key];
        if (val === undefined) {
          val = translations.en;
          for (const k of keys) {
            val = val?.[k];
          }
          return typeof val === "string" ? val : path;
        }
      }
      return typeof val === "string" ? val : path;
    },
    [lang]
  );

  const changeLang = (newLang: Lang) => {
    setLang(newLang);
    localStorage.setItem("devin-lang", newLang);
  };

  return { t, lang, changeLang };
}
