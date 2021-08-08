import {Menu} from './module/menu.js';

((win, doc) => {
    const menuEl = doc.querySelectorAll('.js-menu');

    menuEl.forEach((el, index) => {
        const menu = new Menu(el, index);

        menu.init();
    });

    /** ***************************************************************************************************** */

})(window, document);
