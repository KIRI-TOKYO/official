import {Menu} from './module/menu.js';
import {Tab} from './module/tab.js';
import {Modal} from './module/modal.js';

((win, doc) => {
    const menuEl = doc.querySelectorAll('.js-menu');

    menuEl.forEach((el, index) => {
        const menu = new Menu(el, index);

        menu.init();
    });

    /** ***************************************************************************************************** */

    const tabEl = doc.querySelectorAll('.js-tab');

    tabEl.forEach((el, index) => {
        const tab = new Tab(el, index);

        tab.init();
    });

    /** ***************************************************************************************************** */

    const modalEl = doc.querySelectorAll('.js-modal');

    modalEl.forEach((el, index) => {
        const modal = new Modal(el, index);

        modal.init();
    });
})(window, document);
