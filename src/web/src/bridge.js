export function makeCallApi(tauriCore) {
  return function callApi(name, ...args) {
    const fn = window.pykaraoke_api;
    if (typeof fn !== 'function') throw new Error('engine not ready');
    const proxy = fn(name, ...args);
    if (proxy == null) return null;
    if (proxy.toJs) {
      const value = proxy.toJs({ dict_converter: Object.fromEntries });
      proxy.destroy();
      return value;
    }
    return proxy;
  };
}
