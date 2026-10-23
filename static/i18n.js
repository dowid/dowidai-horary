(() => {
  const {language, locale, languages, messages} = window.HORARY_LOCALE;
  const t = (key, values = {}) => (messages[key] || key).replace(/\{(\w+)\}/g, (match, name) => Object.hasOwn(values, name) ? String(values[name]) : match);
  window.HoraryI18n = {language, locale, t};
  const select = document.getElementById('languageSelect');
  if (select) select.addEventListener('change', () => {
    const pieces = location.pathname.split('/').filter(Boolean);
    if (languages.includes(pieces[0])) pieces.shift();
    const path = pieces.length ? '/' + pieces.join('/') : '';
    location.assign('/' + select.value + path + location.search + location.hash);
  });
})();
