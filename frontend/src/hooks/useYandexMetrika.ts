import { useEffect } from 'react';
import { useLocation } from 'react-router-dom';

const YANDEX_METRIKA_ID = 104667115;

// Расширяем типы Window для Яндекс Метрики
declare global {
  interface Window {
    ym?: (
      counterId: number,
      method: string,
      ...args: any[]
    ) => void;
  }
}

/**
 * Хук для автоматического отслеживания переходов между страницами в SPA
 * Документация: https://yandex.ru/support/metrica/ru/code/counter-spa-setup.html
 */
export function useYandexMetrika() {
  const location = useLocation();

  useEffect(() => {
    // Проверяем, что Яндекс Метрика загружена
    if (typeof window.ym === 'function') {
      // Формируем полный URL страницы
      const url = window.location.origin + location.pathname + location.search + location.hash;

      // Отправляем хит в Яндекс Метрику
      window.ym(YANDEX_METRIKA_ID, 'hit', url, {
        title: document.title,
        referer: document.referrer
      });

      // Логируем в консоль для отладки (можно убрать в продакшене)
      if (process.env.NODE_ENV === 'development') {
        console.log('[Yandex Metrika] Page view tracked:', url);
      }
    } else {
      // Если метрика еще не загружена, ждем и повторяем
      const checkYm = setInterval(() => {
        if (typeof window.ym === 'function') {
          clearInterval(checkYm);
          const url = window.location.origin + location.pathname + location.search + location.hash;
          window.ym(YANDEX_METRIKA_ID, 'hit', url, {
            title: document.title,
            referer: document.referrer
          });
        }
      }, 100);

      // Очищаем интервал через 5 секунд
      setTimeout(() => clearInterval(checkYm), 5000);
    }
  }, [location.pathname, location.search, location.hash]);
}

/**
 * Функция для отправки пользовательских целей
 * Использование: reachGoal('button_click')
 */
export function reachGoal(target: string, params?: Record<string, any>) {
  if (typeof window.ym === 'function') {
    window.ym(YANDEX_METRIKA_ID, 'reachGoal', target, params);

    if (process.env.NODE_ENV === 'development') {
      console.log('[Yandex Metrika] Goal reached:', target, params);
    }
  }
}

/**
 * Функция для отправки параметров визита
 * Использование: setUserParams({userId: '123'})
 */
export function setUserParams(params: Record<string, any>) {
  if (typeof window.ym === 'function') {
    window.ym(YANDEX_METRIKA_ID, 'userParams', params);

    if (process.env.NODE_ENV === 'development') {
      console.log('[Yandex Metrika] User params set:', params);
    }
  }
}
