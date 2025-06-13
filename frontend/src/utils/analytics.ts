export function trackPageView(to: RouteLocationNormalizedLoaded) {
  navigator.sendBeacon(
    '/api/metrics/track',
    JSON.stringify({
      event: 'page_view',
      path:  to.fullPath,
      title: document.title,
      ts:    Date.now(),
      uid:   localStorage.getItem('uuid') ?? 'anon',
    }),
  );
}