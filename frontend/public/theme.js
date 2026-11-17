// Runs before styles and React so the first painted frame uses the chosen theme.
(function () {
  var preference = 'system';
  try {
    var saved = localStorage.getItem('nfl-research-theme');
    if (saved === 'light' || saved === 'dark' || saved === 'system') preference = saved;
  } catch (_) { /* Storage may be unavailable; system remains the default. */ }
  var dark = preference === 'dark' || (preference === 'system' &&
    typeof matchMedia === 'function' && matchMedia('(prefers-color-scheme: dark)').matches);
  document.documentElement.classList.toggle('dark', dark);
  document.documentElement.style.colorScheme = dark ? 'dark' : 'light';
})();
