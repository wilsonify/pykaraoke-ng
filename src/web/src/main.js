import './styles.css';

import { boot } from './boot.js';
import { wireUi } from './ui/wire-ui.js';

function main() {
  wireUi();
  boot();
}

if (typeof document !== 'undefined') {
  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', main);
  } else {
    main();
  }
}
